import re
from pathlib import Path

"""
Direct compiler: loGLang/execute.lbc.txt -> NASM x64 (Windows/Win64).

Важно:
- execute.lbc.txt читается напрямую. Промежуточные lrm/wrm/rlm/rwm/wam/... не создаются.
- logbscd.py не используется и не изменяется.
- r0 — постоянный ноль. r1..r16 — виртуальные 64-битные регистры,
  хранящиеся в .bss, поэтому вызовы Win64 ABI не портят их.
- Адреса вида &123 — смещения в виртуальной RAM, а не сырые адреса процесса.
- ram* с адресом-регистром также работают как смещение в виртуальную RAM.
- "exec \"program.exe [args]\"" / "run" / global "program.exe" запускают EXE через CRT system().
"""

RUNFILE = Path(__file__).resolve().parent
INPUTFILE = RUNFILE / "execute.lbc.txt"
OUTPUTFILE = RUNFILE / "main.asm"

# Каталоги внешних модулей. Приоритет: ./modules -> ./module -> каталог скрипта.
MODULE_DIRS = (
    RUNFILE / "modules",
    RUNFILE / "module",
    RUNFILE,
)

# Размер виртуальной RAM языка.
RAM_SIZE = 1024 * 1024

# r0 оставляем специальным нулевым регистром.
VREG_MIN = 1
VREG_MAX = 16
VREG_SLOTS = VREG_MAX - VREG_MIN + 1

REGISTER_RE = re.compile(r"\br(\d+)\b", re.I)
NUMBER_RE = re.compile(r"'(-?\d+(?:\.\d+)?)'")
MODE_RE = re.compile(r'"([a-zA-Z])"')
PORT_RE = re.compile(r"\bP(\d+)\b", re.I)
ADDR_RE = re.compile(r"&(\d+)")
LABEL_REF_RE = re.compile(r"#([A-Za-z_][A-Za-z0-9_]*)")
LABEL_DEF_RE = re.compile(r"\[([^\]]+)\]")
STRING_RE = re.compile(r'"((?:\\.|[^"\\])*)"')
OP_RE = re.compile(r"(?<![<>!=])([+\-*/])(?![=])")


def strip_inline_comment(line: str) -> str:
    """Удаляет ;-комментарий, но сохраняет ; внутри строк."""
    in_quote = False
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_quote:
            escaped = True
            continue
        if ch == '"':
            in_quote = not in_quote
            continue
        if ch == ";" and not in_quote:
            return line[:i]
    return line


def clean_line(line: str) -> str:
    return strip_inline_comment(line).strip()


def normalize_label(raw: str) -> str:
    raw = raw.strip().replace("#", "")
    raw = re.sub(r"[^A-Za-z0-9_]", "_", raw)
    if not raw:
        raise ValueError("Пустая метка")
    if raw[0].isdigit():
        raw = "L_" + raw
    return raw


def parse_string_token(line: str) -> str | None:
    m = STRING_RE.search(line)
    return m.group(1) if m else None


def nasm_db_bytes(value: str) -> str:
    """Безопасно кодирует строку для NASM через числовые байты."""
    data = value.encode("utf-8")
    return ", ".join(f"0x{b:02X}" for b in data)

def regs_in(line: str) -> list[int]:
    result = [int(x) for x in REGISTER_RE.findall(line)]
    for r in result:
        if r < 0 or r > VREG_MAX:
            raise ValueError(f"r{r}: допустимы r0..r{VREG_MAX}")
    return result


def number_in(line: str) -> int | None:
    m = NUMBER_RE.search(line)
    if not m:
        return None
    raw = m.group(1)
    if "." in raw:
        return int(float(raw))
    return int(raw)


def all_numbers_in(line: str) -> list[int]:
    return [int(float(x)) if "." in x else int(x) for x in NUMBER_RE.findall(line)]


def mode_in(line: str) -> str | None:
    m = MODE_RE.search(line)
    return m.group(1).lower() if m else None


def port_in(line: str) -> int | None:
    m = PORT_RE.search(line)
    return int(m.group(1)) if m else None


def addr_in(line: str) -> int | None:
    m = ADDR_RE.search(line)
    return int(m.group(1)) if m else None


def label_ref_in(line: str) -> str | None:
    m = LABEL_REF_RE.search(line)
    return normalize_label(m.group(1)) if m else None


def label_def_in(line: str) -> str | None:
    m = LABEL_DEF_RE.search(line)
    return normalize_label(m.group(1)) if m else None


def vreg_slot(r: int) -> str:
    if r == 0:
        raise ValueError("r0 не имеет хранилища: это постоянный ноль")
    if not (VREG_MIN <= r <= VREG_MAX):
        raise ValueError(f"r{r}: допустимы r0..r{VREG_MAX}")
    return f"[rel vreg{r}]"


def load_vreg(r: int, scratch: str) -> list[str]:
    if r == 0:
        return [f"    xor {scratch}, {scratch}"]
    return [f"    mov {scratch}, qword {vreg_slot(r)}"]


def store_vreg(r: int, scratch: str) -> list[str]:
    if r == 0:
        return [f"    ; запись в r0 игнорируется: r0 == 0"]
    return [f"    mov qword {vreg_slot(r)}, {scratch}"]


def check_numeric_addr(addr: int, width: int) -> None:
    if addr < 0 or addr + width > RAM_SIZE:
        raise ValueError(
            f"Адрес &{addr} выходит за пределы виртуальной RAM "
            f"(размер {RAM_SIZE}, операция {width} байт)"
        )


def ram_base(scratch: str) -> list[str]:
    return [f"    lea {scratch}, [rel ram]"]


def emit_ram_load_reg(out: list[str], dest: int, addr_reg: int, width: int = 8) -> None:
    # r10 = base, r11 = offset/address, rax = loaded value
    out.extend(load_vreg(addr_reg, "r11"))
    out.append(f"    cmp r11, {RAM_SIZE - width}")
    out.append("    ja __ram_oob")
    out.extend(ram_base("r10"))
    if width == 1:
        out.append("    movzx rax, byte [r10 + r11]")
    elif width == 2:
        out.append("    movzx rax, word [r10 + r11]")
    elif width == 4:
        out.append("    mov eax, dword [r10 + r11]")
    else:
        out.append("    mov rax, qword [r10 + r11]")
    out.extend(store_vreg(dest, "rax"))


def emit_ram_store_reg(out: list[str], addr_reg: int, src_reg: int, width: int = 8) -> None:
    # r10 = base, r11 = offset/address, rax = value
    out.extend(load_vreg(addr_reg, "r11"))
    out.append(f"    cmp r11, {RAM_SIZE - width}")
    out.append("    ja __ram_oob")
    out.extend(load_vreg(src_reg, "rax"))
    out.extend(ram_base("r10"))
    if width == 1:
        out.append("    mov byte [r10 + r11], al")
    elif width == 2:
        out.append("    mov word [r10 + r11], ax")
    elif width == 4:
        out.append("    mov dword [r10 + r11], eax")
    else:
        out.append("    mov qword [r10 + r11], rax")


def emit_ram_load_const(out: list[str], dest: int, addr: int, width: int = 8) -> None:
    check_numeric_addr(addr, width)
    out.extend(ram_base("r10"))
    if width == 1:
        out.append(f"    movzx rax, byte [r10 + {addr}]")
    elif width == 2:
        out.append(f"    movzx rax, word [r10 + {addr}]")
    elif width == 4:
        out.append(f"    mov eax, dword [r10 + {addr}]")
    else:
        out.append(f"    mov rax, qword [r10 + {addr}]")
    out.extend(store_vreg(dest, "rax"))


def emit_ram_store_const(out: list[str], addr: int, value: int, width: int = 8) -> None:
    check_numeric_addr(addr, width)
    out.extend(ram_base("r10"))
    if width == 1:
        out.append(f"    mov byte [r10 + {addr}], {value & 0xFF}")
    elif width == 2:
        out.append(f"    mov word [r10 + {addr}], {value & 0xFFFF}")
    elif width == 4:
        out.append(f"    mov dword [r10 + {addr}], {value & 0xFFFFFFFF}")
    else:
        out.append(f"    mov rax, {value}")
        out.append(f"    mov qword [r10 + {addr}], rax")


def split_array(line: str) -> list[str]:
    m = re.search(r"\[(.*?)\]", line)
    if not m:
        return []
    return [x.strip() for x in m.group(1).split(",") if x.strip()]


def emit_printf_reg(out: list[str], r: int) -> None:
    out.extend(load_vreg(r, "rdx"))
    out.append("    lea rcx, [rel fmt_int]")
    out.append("    call printf")
    out.append("    mov ecx, 10")
    out.append("    call putchar")


def emit_printf_num(out: list[str], value: int) -> None:
    out.append(f"    mov rdx, {value}")
    out.append("    lea rcx, [rel fmt_int]")
    out.append("    call printf")
    out.append("    mov ecx, 10")
    out.append("    call putchar")


def resolve_program(program: str) -> Path | None:
    """Ищет внешний файл прежде всего в ./modules, затем ./module и рядом со скриптом."""
    raw = program.strip().strip('"')
    candidate = Path(raw)

    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()

    checks: list[Path] = []
    # Если в имени уже есть относительный путь (например modules/nmm.exe),
    # проверяем его относительно каталога компилятора.
    checks.append(RUNFILE / candidate)

    # Для простого имени nmm.exe ищем по каталогам модулей.
    if len(candidate.parts) == 1:
        for directory in MODULE_DIRS:
            checks.append(directory / candidate.name)

    seen: set[Path] = set()
    for path in checks:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path.absolute()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def format_system_command(command: str) -> str:
    """Подменяет имя .exe в начале команды найденным файлом из modules."""
    m = re.match(r'^\s*(?:"([^"]+)"|(\S+))(.*)$', command)
    if not m:
        return command

    program = m.group(1) or m.group(2)
    rest = m.group(3) or ""
    if not program.lower().endswith(".exe"):
        return command

    resolved = resolve_program(program)
    if resolved is None:
        # Оставляем исходную команду: system() сам выдаст понятную ошибку.
        return command

    # NASM treats backslash inside db strings as an escape character.
    # Therefore emit a Windows path with forward slashes so a path such as
    # C:\Users\Asus\... cannot be misparsed as an ASM string.
    win_path = resolved.as_posix()
    # system() receives the command line as-is; quoting keeps spaces in paths safe.
    return f'"{win_path}"{rest}'


def emit_exec(out: list[str], command: str, data_lines: list[str], counter: int) -> None:
    command = format_system_command(command)
    label = f"cmd_{counter}"
    encoded = nasm_db_bytes(command)
    if not encoded:
        encoded = "0"
    data_lines.append(f"{label} db {encoded}, 0")
    out.append(f"    lea rcx, [rel {label}]")
    out.append("    call system")


def compile_line(line: str, out: list[str], data_lines: list[str], state: dict) -> bool:
    """Компилирует одну строку execute.lbc.txt напрямую в NASM."""
    line = clean_line(line)
    if not line:
        return False

    # Самодостаточные метки вида [name]
    if line.startswith("[") and line.endswith("]"):
        out.append(f"{label_def_in(line)}:")
        return True

    # Если в строке есть label [name] — это определение, а не память.
    label_def = label_def_in(line)
    if label_def and re.match(r"^\s*(?:label\b|non\b)", line, re.I):
        out.append(f"{label_def}:")
        return True

    m = re.match(r"^(\w+)", line)
    if not m:
        out.append(f"    ; Не разобрано: {line}")
        return True

    cmd = m.group(1).lower()
    regs = regs_in(line)

    if cmd in {"halt", "stop", "hlt"}:
        out.append("    xor ecx, ecx")
        out.append("    call ExitProcess")
        return True

    if cmd in {"exec", "run"}:
        value = parse_string_token(line)
        if value is None:
            raise ValueError(f"{cmd}: ожидается строка в двойных кавычках")
        state["exec_counter"] += 1
        emit_exec(out, value, data_lines, state["exec_counter"])
        return True

    if cmd == "assig":
        if len(regs) < 1:
            raise ValueError("assig: не указан регистр")
        value = number_in(line)
        if value is None:
            raise ValueError("assig: не найдена числовая константа")
        out.append(f"    mov rax, {value}")
        out.extend(store_vreg(regs[0], "rax"))
        return True

    if cmd == "transf":
        if len(regs) < 2:
            raise ValueError("transf: нужны исходный и целевой регистры")
        src, dest = regs[0], regs[1]
        if src == dest:
            return True
        out.extend(load_vreg(src, "rax"))
        out.extend(store_vreg(dest, "rax"))
        return True

    if cmd == "math":
        mode = mode_in(line)
        if mode in {"i", "d"}:
            if not regs:
                raise ValueError("math: не найден регистр")
            value = number_in(line)
            if value is None:
                raise ValueError("math: не найдена константа")
            out.extend(load_vreg(regs[0], "rax"))
            if mode == "i":
                out.append(f"    add rax, {value}")
            else:
                out.append(f"    sub rax, {value}")
            out.extend(store_vreg(regs[0], "rax"))
            return True

        if len(regs) < 3:
            raise ValueError("math: для операции нужны src1, src2, dest")
        src1, src2, dest = regs[:3]
        op = re.search(r"(?<![<>!=])([+\-*/])(?![=])", line)
        if not op:
            raise ValueError("math: не найден оператор + - * /")
        operator = op.group(1)

        out.extend(load_vreg(src1, "rax"))
        out.extend(load_vreg(src2, "rcx"))
        if operator == "+":
            out.append("    add rax, rcx")
        elif operator == "-":
            out.append("    sub rax, rcx")
        elif operator == "*":
            out.append("    mul rcx")
        elif operator == "/":
            out.append("    xor rdx, rdx")
            out.append("    div rcx")
        out.extend(store_vreg(dest, "rax"))
        return True

    if cmd == "go":
        label = label_ref_in(line)
        if not label:
            raise ValueError("go: не найдена метка #name")
        out.append(f"    jmp near {label}")
        return True

    if cmd == "label":
        label = label_ref_in(line)
        if not label:
            raise ValueError("label: не найдена метка #name")
        out.append(f"{label}:")
        return True

    if cmd == "if":
        if len(regs) < 1:
            raise ValueError("if: не найден регистр")
        label = label_ref_in(line)
        if not label:
            raise ValueError("if: не найдена метка #name")
        cond = re.search(r"(=|<|>|\$)", line)
        if not cond:
            raise ValueError("if: поддерживаются =, <, >")
        op = cond.group(1)
        if op == "=":
            if len(regs) >= 2:
                out.extend(load_vreg(regs[0], "rax"))
                out.extend(load_vreg(regs[1], "rcx"))
                out.append("    cmp rax, rcx")
            else:
                value = number_in(line)
                if value is None:
                    raise ValueError("if =: нужен второй регистр или число")
                out.extend(load_vreg(regs[0], "rax"))
                out.append(f"    cmp rax, {value}")
            out.append(f"    je near {label}")
        elif op == "$":
            value = number_in(line)
            if value is None:
                raise ValueError("if $: нужна числовая константа")
            out.extend(load_vreg(regs[0], "rax"))
            out.append(f"    cmp rax, {value}")
            out.append(f"    jne near {label}")
        elif op == ">":
            if len(regs) < 2:
                raise ValueError("if >: нужны два регистра")
            out.extend(load_vreg(regs[0], "rax"))
            out.extend(load_vreg(regs[1], "rcx"))
            out.append("    cmp rax, rcx")
            out.append(f"    jg near {label}")
        else:
            if len(regs) < 2:
                raise ValueError("if <: нужны два регистра")
            out.extend(load_vreg(regs[0], "rax"))
            out.extend(load_vreg(regs[1], "rcx"))
            out.append("    cmp rax, rcx")
            out.append(f"    jl near {label}")
        return True

    if cmd == "raml":
        mode = mode_in(line)
        if mode == "r":
            if not regs:
                raise ValueError("raml \"r\": нужен регистр-приёмник")
            addr = addr_in(line)
            if addr is None:
                raise ValueError("raml \"r\": нужен адрес &N")
            emit_ram_load_const(out, regs[0], addr, 8)
            return True
        if mode == "m":
            if len(regs) < 2:
                raise ValueError("raml \"m\": нужны r_dest и r_addr")
            emit_ram_load_reg(out, regs[0], regs[1], 8)
            return True
        raise ValueError('raml: поддерживаются режимы "r" и "m"')

    if cmd == "ramw":
        mode = mode_in(line)
        if mode == "r":
            if not regs:
                raise ValueError("ramw \"r\": нужен регистр-источник")
            addr = addr_in(line)
            if addr is None:
                raise ValueError("ramw \"r\": нужен адрес &N")
            check_numeric_addr(addr, 8)
            out.extend(load_vreg(regs[0], "rax"))
            out.extend(ram_base("r10"))
            out.append(f"    mov qword [r10 + {addr}], rax")
            return True
        if mode == "n":
            addr = addr_in(line)
            value = number_in(line)
            if addr is None or value is None:
                raise ValueError('ramw "n": нужны &N и числовая константа')
            emit_ram_store_const(out, addr, value, 8)
            return True
        if mode == "m":
            if len(regs) < 2:
                raise ValueError("ramw \"m\": нужны r_src и r_addr")
            emit_ram_store_reg(out, regs[1], regs[0], 8)
            return True
        if mode == "c":
            addr = addr_in(line)
            values = split_array(line)
            if addr is None:
                raise ValueError('ramw "c": нужен адрес &N')
            if addr + len(values) > RAM_SIZE:
                raise ValueError("ramw \"c\": массив выходит за пределы виртуальной RAM")
            out.extend(ram_base("r10"))
            for i, raw in enumerate(values):
                try:
                    value = int(raw.strip("' \""), 0)
                except ValueError as exc:
                    raise ValueError(f"ramw \"c\": плохое значение массива: {raw}") from exc
                out.append(f"    mov byte [r10 + {addr + i}], {value & 0xFF}")
            return True
        raise ValueError('ramw: поддерживаются режимы "r", "n", "m", "c"')

    if cmd == "out":
        mode = mode_in(line)
        port = port_in(line)
        # Автовыбор режима сохраняет логику старого компилятора.
        if mode is None:
            if regs:
                mode = "r"
            elif addr_in(line) is not None:
                mode = "m"
            elif number_in(line) is not None:
                mode = "n"
            elif split_array(line):
                mode = "c"

        if port == 5 and mode == "r":
            if not regs:
                raise ValueError("out r P5: нужен регистр")
            emit_printf_reg(out, regs[0])
            return True
        if port == 5 and mode == "n":
            value = number_in(line)
            if value is None:
                raise ValueError("out n P5: нужна константа")
            emit_printf_num(out, value)
            return True
        if port == 5 and mode == "m":
            addr = addr_in(line)
            if addr is not None:
                check_numeric_addr(addr, 8)
                out.extend(ram_base("r10"))
                out.append(f"    mov rdx, qword [r10 + {addr}]")
                out.append("    lea rcx, [rel fmt_int]")
                out.append("    call printf")
                out.append("    mov ecx, 10")
                out.append("    call putchar")
            elif regs:
                emit_ram_load_reg(out, 0, regs[0], 8)
                emit_printf_reg(out, 0)
            else:
                raise ValueError("out m P5: нужен &N или регистр-адрес")
            return True
        if mode == "c":
            values = split_array(line)
            if not values:
                return True
            for raw in values:
                try:
                    value = int(raw.strip("' \""), 0)
                except ValueError as exc:
                    raise ValueError(f"out c: плохой элемент массива: {raw}") from exc
                if value == 3:
                    out.append("    mov ecx, 10")
                else:
                    out.append(f"    mov ecx, {value & 0xFF}")
                out.append("    call putchar")
            return True
        # Порты 1/2/3/4 пока оставляем без ложных действий.
        out.append(f"    ; out {mode or '?'} P{port if port is not None else '?'}")
        return True

    if cmd == "input":
        if not regs:
            raise ValueError("input: нужен регистр-приёмник")
        port = port_in(line)
        if port in (3, 4):
            out.append("    lea rcx, [rel fmt_char]")
            out.append("    lea rdx, [rel input_char]")
            out.append("    call scanf")
            out.append("    movzx eax, byte [rel input_char]")
        else:
            out.append("    lea rcx, [rel fmt_int]")
            out.append("    lea rdx, [rel input_val]")
            out.append("    call scanf")
            out.append("    mov rax, qword [rel input_val]")
        out.extend(store_vreg(regs[0], "rax"))
        return True

    if cmd == "global":
        value = parse_string_token(line)
        if value is None:
            raise ValueError("global: ожидается имя в кавычках")
        if value.lower() == "return":
            out.append("    jmp near __return")
        elif value.lower().endswith(".exe"):
            # global "nmm.exe" = запуск внешнего модуля, а не call nmm_exe.
            state["exec_counter"] += 1
            emit_exec(out, value, data_lines, state["exec_counter"])
        else:
            # Обычный global остаётся вызовом ASM-метки.
            out.append(f"    call {normalize_label(value)}")
        return True

    if cmd == "section":
        # В execute.lbc.txt это служебная директива; секции создаёт сам генератор.
        out.append(f"    ; section: {line}")
        return True

    if cmd in {"sht", "lrm", "wrm", "rlm", "rwm", "wam", "adi", "sbi", "brh", "brm", "brp", "brn", "orp", "onp", "omp", "irp", "gmp", "ldi", "mov", "add", "sub", "mul", "div", "wnm", "non"}:
        raise ValueError(
            f"Найдена промежуточная мнемоника '{cmd}'. "
            "В новом конвейере execute.lbc.txt должен компилироваться напрямую."
        )

    raise ValueError(f"Неизвестная команда: {cmd}")


def build_asm(source_lines: list[str]) -> str:
    body: list[str] = []
    data_lines: list[str] = []
    state = {"exec_counter": 0}

    for source_line_no, line in enumerate(source_lines, 1):
        try:
            compile_line(line, body, data_lines, state)
        except Exception as exc:
            raise ValueError(f"execute.lbc.txt:{source_line_no}: {exc}") from exc

    lines: list[str] = []
    lines.append("; NASM x64 generated directly from execute.lbc.txt")
    lines.append("; Build (MinGW): nasm -f win64 main.asm -o main.obj && gcc main.obj -o main.exe")
    lines.append("")
    lines.append("default rel")
    lines.append("global main")
    lines.append("extern ExitProcess")
    lines.append("extern printf")
    lines.append("extern scanf")
    lines.append("extern putchar")
    lines.append("extern system")
    lines.append("")

    lines.append("section .data")
    lines.append('    fmt_int db "%lld", 0')
    lines.append('    fmt_char db "%c", 0')
    lines.append('    msg_ram_oob db "RAM out of bounds", 10, 0')
    for dl in data_lines:
        lines.append(f"    {dl}")
    lines.append("")

    lines.append("section .bss")
    lines.append(f"    ram resb {RAM_SIZE}")
    for r in range(1, VREG_MAX + 1):
        lines.append(f"    vreg{r} resq 1")
    lines.append("    input_val resq 1")
    lines.append("    input_char resb 1")
    lines.append("")

    lines.append("section .text")
    lines.append("main:")
    # Win64: 32-byte shadow space + alignment before CALLs.
    lines.append("    sub rsp, 40")

    # main — единственная точка входа, которую создаёт генератор.
    # execute.lbc.txt может содержать [main], label #main или raw main:.
    # Повторное определение main в сгенерированный ASM не выводим.
    reserved_labels = {"main", "__return", "__ram_oob"}
    seen_labels: set[str] = set()

    for item in body:
        stripped = item.strip()
        if stripped == "__RETURN_SENTINEL__":
            continue

        # NASM label definition: "name:"
        if stripped.endswith(":") and not stripped.startswith(";"):
            label = stripped[:-1].strip()
            if label in reserved_labels:
                if label == "main":
                    continue
                raise ValueError(
                    f"execute.lbc.txt содержит зарезервированную метку '{label}'"
                )
            if label in seen_labels:
                raise ValueError(
                    f"execute.lbc.txt: метка '{label}' определена более одного раза"
                )
            seen_labels.add(label)

        lines.append(item)
    lines.append("__return:")
    lines.append("    add rsp, 40")
    lines.append("    xor eax, eax")
    lines.append("    ret")
    lines.append("")

    lines.append("__ram_oob:")
    lines.append("    lea rcx, [rel msg_ram_oob]")
    lines.append("    call printf")
    lines.append("    mov ecx, 1")
    lines.append("    call ExitProcess")
    lines.append("    ud2")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    if not INPUTFILE.exists():
        raise FileNotFoundError(f"Не найден входной файл: {INPUTFILE}")

    source = INPUTFILE.read_text(encoding="utf-8").splitlines()
    asm = build_asm(source)
    OUTPUTFILE.write_text(asm, encoding="utf-8")
    print(f"Скомпилировано напрямую: {INPUTFILE.name} -> {OUTPUTFILE.name}")
    print(f"Виртуальная RAM: {RAM_SIZE} байт; регистры: r0..r{VREG_MAX}")


if __name__ == "__main__":
    main()
