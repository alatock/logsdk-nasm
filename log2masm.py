import re
from pathlib import Path

"""
Direct compiler: execute.lbc.txt -> NASM x64 (Windows/Win64).

Ключевые свойства:
- execute.lbc.txt компилируется напрямую, без промежуточных мнемоник.
- logbscd.py не используется и не изменяется.
- r0 — постоянный ноль; r1..r16 — виртуальные 64-битные регистры в .bss.
- &N — смещение внутри виртуальной RAM.
- ramw "c" пишет байты.
- raml "m" читает ОДИН байт — это нужно для строк ASCII в RAM.
- out "r" P3 выводит один ASCII-символ.
- global/exec/run запускают внешний .exe напрямую через CreateProcessA.
- Передача регистров и диапазонов RAM во внешний .exe отключена.
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

RAM_SIZE = 1024 * 1024
VREG_MIN = 1
VREG_MAX = 16

REGISTER_RE = re.compile(r"\br(\d+)\b", re.I)
NUMBER_RE = re.compile(r"'(-?\d+(?:\.\d+)?)'")
MODE_RE = re.compile(r'"([a-zA-Z])"')
PORT_RE = re.compile(r"\bP(\d+)\b", re.I)
ADDR_RE = re.compile(r"&(\d+)")
RANGE_RE = re.compile(r"(?<!\w)(\d+)\s*:\s*(\d+)(?!\w)")
LABEL_REF_RE = re.compile(r"#([A-Za-z_][A-Za-z0-9_]*)")
LABEL_DEF_RE = re.compile(r"\[([^\]]+)\]")
STRING_RE = re.compile(r'"((?:\\.|[^"\\])*)"')

def strip_inline_comment(line: str) -> str:
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
    data = value.encode("utf-8")
    return ", ".join(f"0x{b:02X}" for b in data) or "0"


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
    return int(float(raw)) if "." in raw else int(raw)


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
        return ["    ; запись в r0 игнорируется: r0 == 0"]
    return [f"    mov qword {vreg_slot(r)}, {scratch}"]


def check_numeric_addr(addr: int, width: int = 1) -> None:
    if addr < 0 or addr + width > RAM_SIZE:
        raise ValueError(
            f"Адрес &{addr} выходит за пределы виртуальной RAM "
            f"(размер {RAM_SIZE}, операция {width} байт)"
        )


def ram_base(scratch: str) -> list[str]:
    return [f"    lea {scratch}, [rel ram]"]


def emit_ram_load_reg(out: list[str], dest: int, addr_reg: int, width: int = 1) -> None:
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


def emit_ram_load_const(out: list[str], dest: int, addr: int, width: int = 1) -> None:
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


def emit_putchar_reg(out: list[str], r: int) -> None:
    out.extend(load_vreg(r, "rax"))
    out.append("    mov ecx, eax")
    out.append("    call putchar")


def resolve_program(program: str) -> Path | None:
    """Находит внешний EXE. Разрешает имя, полный путь и путь без .exe."""
    raw = program.strip().strip('"')
    candidate = Path(raw)
    checks: list[Path] = []

    def add(base: Path) -> None:
        checks.append(base)
        if base.suffix.lower() != '.exe':
            checks.append(Path(str(base) + '.exe'))
        if base.is_dir():
            checks.append(base / (base.name + '.exe'))

    if candidate.is_absolute():
        add(candidate)
    else:
        add(RUNFILE / candidate)
        if len(candidate.parts) == 1:
            for directory in MODULE_DIRS:
                add(directory / candidate.name)

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


def best_effort_program_path(program: str) -> Path:
    """Возвращает путь даже если EXE ещё отсутствует в среде компилятора."""
    found = resolve_program(program)
    if found is not None:
        return found
    raw = program.strip().strip('"')
    candidate = Path(raw)
    if not candidate.is_absolute():
        if len(candidate.parts) == 1:
            # modules имеет приоритет, как договорились.
            candidate = MODULE_DIRS[0] / candidate
        else:
            candidate = RUNFILE / candidate
    if candidate.suffix.lower() != '.exe':
        candidate = Path(str(candidate) + '.exe')
    return candidate.resolve()


def split_exec_program(command: str) -> tuple[str, str]:
    """Выделяет имя/путь EXE и необязательный хвост аргументов."""
    m = re.match(r'^\s*(?:"([^"]+)"|(\S+))(.*)$', command)
    if not m:
        return command.strip().strip('"'), ''
    program = m.group(1) or m.group(2)
    rest = (m.group(3) or '').strip()
    return program, rest


def emit_create_process_wait(
    out: list[str],
    data_lines: list[str],
    exe_path: str,
    args: str,
    call_id: int,
) -> None:
    """Запускает EXE напрямую через CreateProcessA, без cmd.exe."""
    exe_label = f'exe_{call_id}'
    args_label = f'exe_args_{call_id}'
    data_lines.append(f'{exe_label} db {nasm_db_bytes(exe_path)}, 0')
    data_lines.append(f'{args_label} db {nasm_db_bytes(args)}, 0')

    out.extend([
        '    mov dword [rel child_startup_info], 104',
        f'    lea rcx, [rel {exe_label}]',
        f'    lea rdx, [rel {args_label}]',
        '    xor r8d, r8d',
        '    xor r9d, r9d',
        '    mov qword [rsp + 32], 0',
        '    mov qword [rsp + 40], 0',
        '    mov qword [rsp + 48], 0',
        '    mov qword [rsp + 56], 0',
        '    lea rax, [rel child_startup_info]',
        '    mov qword [rsp + 64], rax',
        '    lea rax, [rel child_process_info]',
        '    mov qword [rsp + 72], rax',
        '    call CreateProcessA',
        '    test eax, eax',
        f'    jz near __exec_error_{call_id}',
        '    mov rcx, qword [rel child_process_info]',
        '    mov edx, 0xFFFFFFFF',
        '    call WaitForSingleObject',
        '    mov rcx, qword [rel child_process_info]',
        '    call CloseHandle',
        '    mov rcx, qword [rel child_process_info + 8]',
        '    call CloseHandle',
        f'    jmp near __exec_done_{call_id}',
        f'__exec_error_{call_id}:',
        '    lea rcx, [rel msg_exec_error]',
        '    call printf',
        '    mov ecx, 1',
        '    call ExitProcess',
        f'__exec_done_{call_id}:',
    ])

def emit_printf_error(out: list[str], label: str, message_label: str) -> None:
    out.extend([
        f"{label}:",
        f"    lea rcx, [rel {message_label}]",
        "    call printf",
        "    mov ecx, 1",
        "    call ExitProcess",
        "    ud2",
    ])


def compile_line(line: str, out: list[str], data_lines: list[str], state: dict) -> bool:
    line = clean_line(line)
    if not line:
        return False

    if line.startswith("[") and line.endswith("]"):
        out.append(f"{label_def_in(line)}:")
        return True

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

    if cmd in {"exec", "run", "global"}:
        value = parse_string_token(line)
        if value is None:
            if cmd == "global":
                raise ValueError("global: ожидается имя в кавычках")
            raise ValueError(f"{cmd}: ожидается строка в двойных кавычках")

        if cmd == "global" and value.lower() == "return":
            out.append("    jmp near __return")
            return True

        # Только запуск внешнего EXE. Передача rN и диапазонов RAM намеренно отключена.
        first_program = re.match(r'^\s*(?:"([^"]+)"|(\S+))', value)
        program_token = (first_program.group(1) or first_program.group(2)) if first_program else value.strip()
        is_exe = program_token.lower().endswith(".exe") or resolve_program(program_token) is not None
        if not is_exe:
            if cmd == "global":
                out.append(f"    call {normalize_label(value)}")
                return True
            raise ValueError(f"{cmd}: ожидается путь/имя внешнего .exe")

        state["exec_counter"] += 1
        call_id = state["exec_counter"]
        program, rest = split_exec_program(value)
        normalized_path = best_effort_program_path(program)
        command_line = f'"{normalized_path.as_posix()}"' + (f' {rest}' if rest else '')
        emit_create_process_wait(
            out, data_lines, normalized_path.as_posix(), command_line, call_id
        )
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
        src, dest = regs[:2]
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
            out.append(f"    {'add' if mode == 'i' else 'sub'} rax, {value}")
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
        if not regs:
            raise ValueError("if: не найден регистр")
        label = label_ref_in(line)
        if not label:
            raise ValueError("if: не найдена метка #name")
        cond = re.search(r"(=|<|>|\$)", line)
        if not cond:
            raise ValueError("if: поддерживаются =, <, >, $")
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
        else:
            if len(regs) < 2:
                raise ValueError(f"if {op}: нужны два регистра")
            out.extend(load_vreg(regs[0], "rax"))
            out.extend(load_vreg(regs[1], "rcx"))
            out.append("    cmp rax, rcx")
            out.append(f"    {'jg' if op == '>' else 'jl'} near {label}")
        return True

    if cmd == "raml":
        mode = mode_in(line)
        if mode == "r":
            if not regs:
                raise ValueError('raml "r": нужен регистр-приёмник')
            addr = addr_in(line)
            if addr is None:
                raise ValueError('raml "r": нужен адрес &N')
            emit_ram_load_const(out, regs[0], addr, 1)
            return True
        if mode == "m":
            if len(regs) < 2:
                raise ValueError('raml "m": нужны r_dest и r_addr')
            # ASCII/byte memory cell.
            emit_ram_load_reg(out, regs[0], regs[1], 1)
            return True
        raise ValueError('raml: поддерживаются режимы "r" и "m"')

    if cmd == "ramw":
        mode = mode_in(line)
        if mode == "r":
            if not regs:
                raise ValueError('ramw "r": нужен регистр-источник')
            addr = addr_in(line)
            if addr is None:
                raise ValueError('ramw "r": нужен адрес &N')
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
            # Числовая запись по одному memory-cell.
            emit_ram_store_const(out, addr, value, 1)
            return True
        if mode == "m":
            if len(regs) < 2:
                raise ValueError('ramw "m": нужны r_src и r_addr')
            emit_ram_store_reg(out, regs[1], regs[0], 8)
            return True
        if mode == "c":
            addr = addr_in(line)
            values = split_array(line)
            if addr is None:
                raise ValueError('ramw "c": нужен адрес &N')
            if addr + len(values) > RAM_SIZE:
                raise ValueError('ramw "c": массив выходит за пределы виртуальной RAM')
            out.extend(ram_base("r10"))
            for i, raw in enumerate(values):
                try:
                    value = int(raw.strip("' \""), 0)
                except ValueError as exc:
                    raise ValueError(f'ramw "c": плохое значение массива: {raw}') from exc
                out.append(f"    mov byte [r10 + {addr + i}], {value & 0xFF}")
            return True
        raise ValueError('ramw: поддерживаются режимы "r", "n", "m", "c"')

    if cmd == "out":
        mode = mode_in(line)
        port = port_in(line)
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
            return True

        # P3 — ASCII output. Это нужно для text_out.exe.
        if port == 3 and mode == "r":
            if not regs:
                raise ValueError('out "r" P3: нужен регистр')
            emit_putchar_reg(out, regs[0])
            return True
        if port == 3 and mode == "n":
            value = number_in(line)
            if value is None:
                raise ValueError('out "n" P3: нужна константа')
            out.append(f"    mov ecx, {value & 0xFF}")
            out.append("    call putchar")
            return True
        if port == 3 and mode == "c":
            for raw in split_array(line):
                try:
                    value = int(raw.strip("' \""), 0)
                except ValueError:
                    continue
                out.append(f"    mov ecx, {value & 0xFF}")
                out.append("    call putchar")
            return True

        if mode == "c":
            for raw in split_array(line):
                try:
                    value = int(raw.strip("' \""), 0)
                except ValueError as exc:
                    raise ValueError(f"out c: плохой элемент массива: {raw}") from exc
                out.append(f"    mov ecx, {10 if value == 3 else value & 0xFF}")
                out.append("    call putchar")
            return True

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

    if cmd == "section":
        out.append(f"    ; section: {line}")
        return True

    if cmd in {"sht", "lrm", "wrm", "rlm", "rwm", "wam", "adi", "sbi",
               "brh", "brm", "brp", "brn", "orp", "onp", "omp", "irp",
               "gmp", "ldi", "mov", "add", "sub", "mul", "div", "wnm", "non"}:
        raise ValueError(
            f"Найдена промежуточная мнемоника '{cmd}'. "
            "execute.lbc.txt должен компилироваться напрямую."
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
    lines += [
        "; NASM x64 generated directly from execute.lbc.txt",
        "; Build: nasm -f win64 main.asm -o main.obj && gcc main.obj -o main.exe",
        "",
        "default rel",
        "global main",
        "extern ExitProcess",
        "extern printf",
        "extern scanf",
        "extern putchar",
        "extern CreateProcessA",
        "extern WaitForSingleObject",
        "extern CloseHandle",
        "",
        "section .data",
        '    fmt_int db "%lld", 0',
        '    fmt_char db "%c", 0',
        '    msg_ram_oob db "RAM out of bounds", 10, 0',
        '    msg_exec_error db "Cannot start external EXE", 10, 0',
    ]
    for dl in data_lines:
        lines.append(f"    {dl}")

    lines += [
        "",
        "section .bss",
        f"    ram resb {RAM_SIZE}",
    ]
    for r in range(1, VREG_MAX + 1):
        lines.append(f"    vreg{r} resq 1")
    lines += [
        "    input_val resq 1",
        "    input_char resb 1",
        "    child_startup_info resb 104",
        "    child_process_info resb 24",
        "",
        "section .text",
        "main:",
        "    sub rsp, 88",
    ]

    reserved_labels = {
        "main", "__return", "__ram_oob",
    }
    seen_labels: set[str] = set()

    for item in body:
        stripped = item.strip()
        if stripped.endswith(":") and not stripped.startswith(";"):
            label = stripped[:-1].strip()
            if label in reserved_labels:
                if label == "main":
                    continue
                raise ValueError(f"execute.lbc.txt содержит зарезервированную метку '{label}'")
            if label in seen_labels:
                raise ValueError(f"execute.lbc.txt: метка '{label}' определена более одного раза")
            seen_labels.add(label)
        lines.append(item)

    # Общая точка возврата.
    lines += [
        "__return:",
        "    add rsp, 88",
        "    xor eax, eax",
        "    ret",
        "",
        "__ram_oob:",
        "    lea rcx, [rel msg_ram_oob]",
        "    call printf",
        "    mov ecx, 1",
        "    call ExitProcess",
        "    ud2",
        "",
    ]

    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    if not INPUTFILE.exists():
        raise FileNotFoundError(f"Не найден входной файл: {INPUTFILE}")
    source = INPUTFILE.read_text(encoding="utf-8").splitlines()
    asm = build_asm(source)
    OUTPUTFILE.write_text(asm, encoding="utf-8")
    print(f"Скомпилировано напрямую: {INPUTFILE.name} -> {OUTPUTFILE.name}")
    print(f"RAM: {RAM_SIZE} байт; регистры: r0..r{VREG_MAX}")
    print("EXE: global/exec/run \"file.exe\"")


if __name__ == "__main__":
    main()