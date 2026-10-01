; ============================================================================
; ПОЛНАЯ ПАМЯТКА ПО NASM АССЕМБЛЕРУ (x86-64 Windows)
; ============================================================================
; Автор: Справочное руководство для изучения NASM
; Платформа: Windows x64
; Ассемблер: NASM (Netwide Assembler)
; ============================================================================

; ============================================================================
; 1. РЕГИСТРЫ И ИХ НАЗНАЧЕНИЕ
; ============================================================================

; --- РЕГИСТРЫ ОБЩЕГО НАЗНАЧЕНИЯ (64-бит) ---
; RAX (Accumulator) - аккумулятор, результаты операций, возврат из функций
; RBX (Base) - базовый регистр, часто для адресации памяти
; RCX (Counter) - счётчик в циклах, 4-й аргумент функций (Windows x64)
; RDX (Data) - данные, 3-й аргумент функций (Windows x64)
; RSI (Source Index) - индекс источника для строковых операций
; RDI (Destination Index) - индекс назначения для строковых операций
; RBP (Base Pointer) - указатель базы стека (frame pointer)
; RSP (Stack Pointer) - указатель вершины стека (НИКОГДА не использовать напрямую!)

; R8-R15 - дополнительные регистры общего назначения (x64)
; R8 - 5-й аргумент функций (Windows x64)
; R9 - 6-й аргумент функций (Windows x64)

; --- МЛАДШИЕ ЧАСТИ РЕГИСТРОВ ---
; RAX: RAX (64-бит) -> EAX (32-бит) -> AX (16-бит) -> AH (старшие 8 бит) / AL (младшие 8 бит)
; То же для RBX->EBX->BX->BH/BL, RCX->ECX->CX->CH/CL, RDX->EDX->DX->DH/DL

; --- СПЕЦИАЛЬНЫЕ РЕГИСТРЫ ---
; RIP - instruction pointer (указатель на текущую инструкцию)
; RFLAGS - регистр флагов (CF, ZF, SF, OF, PF, AF и др.)

; --- ФЛАГИ В RFLAGS ---
; CF (Carry Flag) - флаг переноса при беззнаковых операциях
; ZF (Zero Flag) - результат операции равен нулю
; SF (Sign Flag) - знаковый бит результата (отрицательное число)
; OF (Overflow Flag) - переполнение при знаковых операциях
; PF (Parity Flag) - чётность младшего байта
; AF (Auxiliary Flag) - вспомогательный перенос (BCD операции)

; --- СЕГМЕНТНЫЕ РЕГИСТРЫ (устаревшие в 64-бит режиме, но существуют) ---
; CS, DS, SS, ES, FS, GS - редко используются в современном коде


; ============================================================================
; 2. МАТЕМАТИЧЕСКИЕ ОПЕРАЦИИ
; ============================================================================

section .text
global _start

math_operations:
    ; --- СЛОЖЕНИЕ ---
    mov rax, 10         ; RAX = 10
    add rax, 5          ; RAX = RAX + 5 = 15
    adc rbx, rcx        ; RBX = RBX + RCX + CF (сложение с переносом)
    
    ; --- ВЫЧИТАНИЕ ---
    mov rax, 20         ; RAX = 20
    sub rax, 7          ; RAX = RAX - 7 = 13
    sbb rbx, rcx        ; RBX = RBX - RCX - CF (вычитание с заёмом)
    neg rax             ; RAX = -RAX (изменение знака)
    
    ; --- ИНКРЕМЕНТ/ДЕКРЕМЕНТ ---
    inc rax             ; RAX = RAX + 1 (быстрее чем add)
    dec rbx             ; RBX = RBX - 1 (быстрее чем sub)
    
    ; --- УМНОЖЕНИЕ ---
    ; Беззнаковое умножение:
    mov rax, 5
    mov rbx, 3
    mul rbx             ; RAX = RAX * RBX, старшие биты в RDX (RAX=15, RDX=0)
    
    ; Знаковое умножение:
    mov rax, -5
    mov rbx, 3
    imul rbx            ; RAX = RAX * RBX (знаковое)
    
    ; Умножение с указанием результата:
    imul rax, rbx, 10   ; RAX = RBX * 10
    imul rax, rbx       ; RAX = RAX * RBX
    
    ; --- ДЕЛЕНИЕ ---
    ; Беззнаковое деление:
    mov rax, 17         ; делимое
    xor rdx, rdx        ; обнулить RDX (старшие биты делимого)
    mov rbx, 5          ; делитель
    div rbx             ; RAX = частное (3), RDX = остаток (2)
    
    ; Знаковое деление:
    mov rax, -17
    cqo                 ; расширить RAX в RDX:RAX с учётом знака
    mov rbx, 5
    idiv rbx            ; RAX = частное, RDX = остаток
    
    ; --- БИТОВЫЕ ОПЕРАЦИИ ---
    mov rax, 0b11001100
    mov rbx, 0b10101010
    
    and rax, rbx        ; RAX = RAX & RBX (побитовое И)
    or  rax, rbx        ; RAX = RAX | RBX (побитовое ИЛИ)
    xor rax, rbx        ; RAX = RAX ^ RBX (побитовое исключающее ИЛИ)
    not rax             ; RAX = ~RAX (побитовое НЕ, инверсия)
    
    ; --- СДВИГИ ---
    mov rax, 8
    shl rax, 2          ; RAX = RAX << 2 = 32 (логический сдвиг влево, умножение на 4)
    shr rax, 1          ; RAX = RAX >> 1 = 16 (логический сдвиг вправо, деление на 2)
    
    sal rax, 1          ; арифметический сдвиг влево (аналогично shl)
    sar rax, 1          ; арифметический сдвиг вправо (сохраняет знак)
    
    ; Циклические сдвиги:
    rol rax, 4          ; циклический сдвиг влево на 4 бита
    ror rax, 2          ; циклический сдвиг вправо на 2 бита
    
    ; Сдвиг через флаг переноса:
    rcl rax, 1          ; сдвиг влево через CF
    rcr rax, 1          ; сдвиг вправо через CF
    
    ; --- СРАВНЕНИЕ ---
    mov rax, 10
    mov rbx, 20
    cmp rax, rbx        ; сравнить RAX и RBX (вычитание без сохранения)
                        ; устанавливает флаги: ZF, SF, CF, OF
    test rax, rax       ; проверка на ноль (RAX & RAX), устанавливает флаги
    
    ; --- ОБМЕН ---
    xchg rax, rbx       ; поменять местами RAX и RBX
    
    ret


; ============================================================================
; 3. ВЕТВЛЕНИЕ И УСЛОВНЫЕ ПЕРЕХОДЫ
; ============================================================================

branching:
    ; --- БЕЗУСЛОВНЫЙ ПЕРЕХОД ---
    jmp label_name      ; переход на метку
    
    ; --- УСЛОВНЫЕ ПЕРЕХОДЫ (после cmp или test) ---
    
    ; Для беззнаковых чисел:
    cmp rax, rbx
    je  equal           ; Jump if Equal (ZF=1)
    jne not_equal       ; Jump if Not Equal (ZF=0)
    jz  zero            ; Jump if Zero (ZF=1, аналогично je)
    jnz not_zero        ; Jump if Not Zero (ZF=0)
    
    ja  above           ; Jump if Above (беззнаковое >)
    jae above_equal     ; Jump if Above or Equal (беззнаковое >=)
    jb  below           ; Jump if Below (беззнаковое <)
    jbe below_equal     ; Jump if Below or Equal (беззнаковое <=)
    
    ; Для знаковых чисел:
    jg  greater         ; Jump if Greater (знаковое >)
    jge greater_equal   ; Jump if Greater or Equal (знаковое >=)
    jl  less            ; Jump if Less (знаковое <)
    jle less_equal      ; Jump if Less or Equal (знаковое <=)
    
    ; Проверка отдельных флагов:
    jc  carry_set       ; Jump if Carry (CF=1)
    jnc no_carry        ; Jump if Not Carry (CF=0)
    jo  overflow        ; Jump if Overflow (OF=1)
    jno no_overflow     ; Jump if Not Overflow (OF=0)
    js  sign_set        ; Jump if Sign (SF=1, отрицательное)
    jns no_sign         ; Jump if Not Sign (SF=0, положительное)
    jp  parity_even     ; Jump if Parity Even (PF=1)
    jnp parity_odd      ; Jump if Parity Odd (PF=0)
    
    ; --- ЦИКЛЫ ---
    mov rcx, 10         ; счётчик цикла
loop_start:
    ; тело цикла
    dec rcx             ; уменьшить счётчик
    jnz loop_start      ; если RCX != 0, повторить
    
    ; Альтернатива с loop:
    mov rcx, 10
loop_alt:
    ; тело цикла
    loop loop_alt       ; автоматически dec rcx и jnz
    
    ; --- ВЫЗОВ ФУНКЦИЙ ---
    call function_name  ; сохранить адрес возврата в стек и перейти
    ret                 ; вернуться из функции (pop RIP)
    
    ; Возврат с очисткой стека:
    ret 16              ; pop RIP и добавить 16 к RSP

equal:
not_equal:
zero:
not_zero:
above:
above_equal:
below:
below_equal:
greater:
greater_equal:
less:
less_equal:
carry_set:
no_carry:
overflow:
no_overflow:
sign_set:
no_sign:
parity_even:
parity_odd:
label_name:
function_name:
    ret


; ============================================================================
; 4. РАБОТА С ПАМЯТЬЮ
; ============================================================================

; --- МОДЕЛЬ ПАМЯТИ ---
; Виртуальная память делится на сегменты:
; - Code (.text) - исполняемый код
; - Data (.data) - инициализированные данные
; - BSS (.bss) - неинициализированные данные
; - Stack - стек (растёт вниз от старших адресов)
; - Heap - куча (динамическая память, растёт вверх)

section .data
    ; --- ИНИЦИАЛИЗИРОВАННЫЕ ДАННЫЕ ---
    byte_var    db 0x12             ; 1 байт (define byte)
    word_var    dw 0x1234           ; 2 байта (define word)
    dword_var   dd 0x12345678       ; 4 байта (define double word)
    qword_var   dq 0x123456789ABCDEF ; 8 байт (define quad word)
    
    ; Массивы:
    array_bytes db 1, 2, 3, 4, 5    ; массив байт
    array_words dw 100, 200, 300    ; массив слов
    
    ; Строки:
    string      db 'Hello, World!', 0  ; строка с нулевым терминатором
    string_len  equ $ - string         ; длина строки ($ - текущий адрес)
    
    ; Резервирование места с инициализацией:
    buffer      times 64 db 0       ; 64 байта, заполненные нулями

section .bss
    ; --- НЕИНИЦИАЛИЗИРОВАННЫЕ ДАННЫЕ ---
    uninit_byte  resb 1             ; резервировать 1 байт
    uninit_word  resw 1             ; резервировать 2 байта
    uninit_dword resd 1             ; резервировать 4 байта
    uninit_qword resq 1             ; резервировать 8 байт
    
    large_buffer resb 1024          ; буфер 1 КБ

section .text

memory_operations:
    ; --- ЗАГРУЗКА ИЗ ПАМЯТИ ---
    mov rax, [qword_var]        ; загрузить 8 байт из памяти в RAX
    mov eax, [dword_var]        ; загрузить 4 байта в EAX
    mov ax,  [word_var]         ; загрузить 2 байта в AX
    mov al,  [byte_var]         ; загрузить 1 байт в AL
    
    ; Загрузка с расширением:
    movzx rax, byte [byte_var]  ; загрузить байт с расширением нулями
    movsx rax, byte [byte_var]  ; загрузить байт с расширением знака
    
    ; --- СОХРАНЕНИЕ В ПАМЯТЬ ---
    mov [qword_var], rax        ; сохранить RAX (8 байт) в память
    mov [dword_var], eax        ; сохранить EAX (4 байта)
    mov [word_var], ax          ; сохранить AX (2 байта)
    mov [byte_var], al          ; сохранить AL (1 байт)
    
    ; --- АДРЕСАЦИЯ ПАМЯТИ ---
    ; Форматы: [base + index*scale + displacement]
    ; base: любой регистр
    ; index: любой регистр кроме RSP
    ; scale: 1, 2, 4, или 8
    ; displacement: константа
    
    lea rax, [array_bytes]      ; загрузить адрес массива (Load Effective Address)
    mov rbx, 2                  ; индекс
    mov cl, [rax + rbx]         ; CL = array_bytes[2]
    
    ; Доступ к массиву с масштабом:
    lea rax, [array_words]
    mov rbx, 1                  ; индекс элемента
    mov cx, [rax + rbx*2]       ; CX = array_words[1] (rbx*2 т.к. word = 2 байта)
    
    ; Относительная адресация (RIP-relative, для 64-бит):
    mov rax, [rel qword_var]    ; загрузить относительно RIP
    
    ; --- РАБОТА СО СТЕКОМ ---
    ; Стек растёт вниз (от старших адресов к младшим)
    
    push rax                    ; RSP -= 8, [RSP] = RAX
    pop rbx                     ; RBX = [RSP], RSP += 8
    
    ; Сохранение/восстановление множества регистров:
    push rax
    push rbx
    push rcx
    ; ... код ...
    pop rcx
    pop rbx
    pop rax
    
    ; Создание стекового фрейма:
    push rbp                    ; сохранить старый base pointer
    mov rbp, rsp                ; установить новый base pointer
    sub rsp, 32                 ; выделить 32 байта для локальных переменных
    
    ; Локальные переменные доступны как [rbp - offset]:
    mov qword [rbp - 8], 100    ; первая локальная переменная
    mov qword [rbp - 16], 200   ; вторая локальная переменная
    
    ; Очистка стекового фрейма:
    mov rsp, rbp                ; восстановить RSP
    pop rbp                     ; восстановить старый RBP
    ret
    
    ; --- СТРОКОВЫЕ ОПЕРАЦИИ ---
    ; Операции работают с RSI (source) и RDI (destination)
    
    lea rsi, [string]           ; источник
    lea rdi, [buffer]           ; назначение
    mov rcx, string_len         ; счётчик
    cld                         ; Direction Flag = 0 (инкремент)
    rep movsb                   ; повторять movsb RCX раз (копирование)
    
    ; Другие строковые операции:
    ; movsb/movsw/movsd/movsq - копирование байта/слова/двойного слова/четверного слова
    ; stosb/stosw/stosd/stosq - запись AL/AX/EAX/RAX в [RDI]
    ; lodsb/lodsw/lodsd/lodsq - загрузка из [RSI] в AL/AX/EAX/RAX
    ; scasb/scasw/scasd/scasq - сравнение AL/AX/EAX/RAX с [RDI]
    ; cmpsb/cmpsw/cmpsd/cmpsq - сравнение [RSI] с [RDI]
    
    ; Префиксы повторения:
    ; rep   - повторять пока RCX != 0
    ; repe/repz  - повторять пока RCX != 0 и ZF = 1
    ; repne/repnz - повторять пока RCX != 0 и ZF = 0
    
    ret


; ============================================================================
; 5. ВЗАИМОДЕЙСТВИЕ С WINDOWS API
; ============================================================================

; --- СОГЛАШЕНИЕ О ВЫЗОВАХ (Windows x64 Calling Convention) ---
; Аргументы функций передаются в:
; RCX - 1-й аргумент
; RDX - 2-й аргумент
; R8  - 3-й аргумент
; R9  - 4-й аргумент
; Остальные аргументы - в стеке (справа налево)
;
; Возвращаемое значение: RAX
;
; Регистры, которые функция ДОЛЖНА сохранять:
; RBX, RBP, RDI, RSI, RSP, R12-R15
;
; Регистры, которые функция может изменять:
; RAX, RCX, RDX, R8-R11
;
; Stack alignment: RSP должен быть выровнен на 16 байт перед call
; Shadow space: нужно выделить 32 байта (4*8) перед вызовом

extern ExitProcess
extern GetStdHandle
extern WriteConsoleA
extern ReadConsoleA
extern CreateProcessA
extern WaitForSingleObject
extern CloseHandle
extern LoadLibraryA
extern GetProcAddress

section .data
    ; Константы WinAPI
    STD_OUTPUT_HANDLE equ -11
    STD_INPUT_HANDLE  equ -10
    INFINITE          equ -1
    
    hello_msg db 'Hello from ASM!', 13, 10, 0
    hello_len equ $ - hello_msg

section .bss
    bytes_written resq 1
    h_stdout resq 1

section .text
global main

main:
    ; Пролог функции
    push rbp
    mov rbp, rsp
    sub rsp, 32             ; shadow space (32 байта обязательно!)
    
    ; --- ПОЛУЧИТЬ ДЕСКРИПТОР КОНСОЛИ ---
    mov rcx, STD_OUTPUT_HANDLE
    call GetStdHandle
    mov [h_stdout], rax
    
    ; --- ВЫВОД В КОНСОЛЬ ---
    ; WriteConsoleA(hConsole, lpBuffer, nCharsToWrite, lpCharsWritten, lpReserved)
    mov rcx, [h_stdout]         ; hConsole
    lea rdx, [hello_msg]        ; lpBuffer
    mov r8, hello_len           ; nCharsToWrite
    lea r9, [bytes_written]     ; lpCharsWritten
    mov qword [rsp+32], 0       ; 5-й аргумент в стеке (lpReserved = NULL)
    call WriteConsoleA
    
    ; --- ЧТЕНИЕ ИЗ КОНСОЛИ ---
    ; Сначала получить дескриптор stdin
    mov rcx, STD_INPUT_HANDLE
    call GetStdHandle
    ; затем ReadConsoleA аналогично WriteConsoleA
    
    ; Эпилог и выход
    xor rcx, rcx            ; exit code = 0
    call ExitProcess


; ============================================================================
; 6. СОЗДАНИЕ И ВЫПОЛНЕНИЕ ПРОЦЕССОВ
; ============================================================================

section .data
    ; Структуры для CreateProcessA
    startup_info:
        dd 68               ; cb (размер структуры STARTUPINFOA)
        times 64 db 0       ; остальные поля (упрощённо)
    
    process_info:
        times 24 db 0       ; PROCESS_INFORMATION (hProcess, hThread, dwProcessId, dwThreadId)
    
    command_line db 'notepad.exe', 0
    exe_path db 'C:\Windows\System32\calc.exe', 0

section .text

execute_process:
    push rbp
    mov rbp, rsp
    sub rsp, 80             ; больше места для параметров
    
    ; --- ЗАПУСК ПРОЦЕССА ---
    ; CreateProcessA(lpApplicationName, lpCommandLine, lpProcessAttr, lpThreadAttr,
    ;                bInheritHandles, dwCreationFlags, lpEnvironment, lpCurrentDir,
    ;                lpStartupInfo, lpProcessInformation)
    
    xor rcx, rcx            ; lpApplicationName = NULL
    lea rdx, [command_line] ; lpCommandLine
    xor r8, r8              ; lpProcessAttr = NULL
    xor r9, r9              ; lpThreadAttr = NULL
    mov qword [rsp+32], 0   ; bInheritHandles = FALSE
    mov qword [rsp+40], 0   ; dwCreationFlags = 0
    mov qword [rsp+48], 0   ; lpEnvironment = NULL
    mov qword [rsp+56], 0   ; lpCurrentDir = NULL
    lea rax, [startup_info]
    mov [rsp+64], rax       ; lpStartupInfo
    lea rax, [process_info]
    mov [rsp+72], rax       ; lpProcessInformation
    call CreateProcessA
    
    test rax, rax
    jz process_failed
    
    ; --- ОЖИДАНИЕ ЗАВЕРШЕНИЯ ПРОЦЕССА ---
    mov rcx, [process_info] ; hProcess
    mov rdx, INFINITE       ; dwMilliseconds
    call WaitForSingleObject
    
    ; --- ЗАКРЫТИЕ ДЕСКРИПТОРОВ ---
    mov rcx, [process_info]     ; hProcess
    call CloseHandle
    mov rcx, [process_info+8]   ; hThread
    call CloseHandle
    
process_failed:
    mov rsp, rbp
    pop rbp
    ret


; ============================================================================
; 7. ЗАГРУЗКА И ИСПОЛЬЗОВАНИЕ DLL (ДИНАМИЧЕСКИХ БИБЛИОТЕК)
; ============================================================================

section .data
    dll_name db 'user32.dll', 0
    func_name db 'MessageBoxA', 0
    
    msg_title db 'Title', 0
    msg_text db 'Hello from DLL!', 0
    
    MB_OK equ 0

section .bss
    h_dll resq 1
    func_ptr resq 1

section .text

use_dll:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    
    ; --- ЗАГРУЗКА DLL ---
    lea rcx, [dll_name]
    call LoadLibraryA
    test rax, rax
    jz dll_failed
    mov [h_dll], rax
    
    ; --- ПОЛУЧЕНИЕ АДРЕСА ФУНКЦИИ ---
    mov rcx, [h_dll]
    lea rdx, [func_name]
    call GetProcAddress
    test rax, rax
    jz dll_failed
    mov [func_ptr], rax
    
    ; --- ВЫЗОВ ФУНКЦИИ ИЗ DLL ---
    ; MessageBoxA(hWnd, lpText, lpCaption, uType)
    xor rcx, rcx            ; hWnd = NULL
    lea rdx, [msg_text]     ; lpText
    lea r8, [msg_title]     ; lpCaption
    mov r9, MB_OK           ; uType
    call [func_ptr]         ; вызов через указатель
    
    ; --- ВЫГРУЗКА DLL ---
    mov rcx, [h_dll]
    call CloseHandle        ; FreeLibrary тоже работает
    
dll_failed:
    mov rsp, rbp
    pop rbp
    ret


; ============================================================================
; 8. РАБОТА С ФАЙЛАМИ (Windows API)
; ============================================================================

extern CreateFileA
extern ReadFile
extern WriteFile

section .data
    filename db 'test.txt', 0
    
    ; Константы CreateFileA
    GENERIC_READ    equ 0x80000000
    GENERIC_WRITE   equ 0x40000000
    FILE_SHARE_READ equ 0x00000001
    CREATE_ALWAYS   equ 2
    OPEN_EXISTING   equ 3
    FILE_ATTRIBUTE_NORMAL equ 0x80
    
    write_data db 'Test data', 13, 10, 0
    write_len equ $ - write_data

section .bss
    h_file resq 1
    bytes_rw resq 1
    read_buffer resb 256

section .text

file_operations:
    push rbp
    mov rbp, rsp
    sub rsp, 48
    
    ; --- СОЗДАНИЕ/ОТКРЫТИЕ ФАЙЛА ---
    lea rcx, [filename]         ; lpFileName
    mov rdx, GENERIC_WRITE      ; dwDesiredAccess
    mov r8, 0                   ; dwShareMode
    xor r9, r9                  ; lpSecurityAttributes = NULL
    mov dword [rsp+32], CREATE_ALWAYS   ; dwCreationDisposition
    mov dword [rsp+40], FILE_ATTRIBUTE_NORMAL ; dwFlagsAndAttributes
    mov qword [rsp+48], 0       ; hTemplateFile = NULL
    call CreateFileA
    
    cmp rax, -1                 ; INVALID_HANDLE_VALUE
    je file_error
    mov [h_file], rax
    
    ; --- ЗАПИСЬ В ФАЙЛ ---
    mov rcx, [h_file]           ; hFile
    lea rdx, [write_data]       ; lpBuffer
    mov r8, write_len           ; nNumberOfBytesToWrite
    lea r9, [bytes_rw]          ; lpNumberOfBytesWritten
    mov qword [rsp+32], 0       ; lpOverlapped = NULL
    call WriteFile
    
    ; --- ЗАКРЫТИЕ ФАЙЛА ---
    mov rcx, [h_file]
    call CloseHandle
    
    ; --- ЧТЕНИЕ ФАЙЛА ---
    lea rcx, [filename]
    mov rdx, GENERIC_READ
    mov r8, FILE_SHARE_READ
    xor r9, r9
    mov dword [rsp+32], OPEN_EXISTING
    mov dword [rsp+40], FILE_ATTRIBUTE_NORMAL
    mov qword [rsp+48], 0
    call CreateFileA
    
    cmp rax, -1
    je file_error
    mov [h_file], rax
    
    mov rcx, [h_file]           ; hFile
    lea rdx, [read_buffer]      ; lpBuffer
    mov r8, 256                 ; nNumberOfBytesToRead
    lea r9, [bytes_rw]          ; lpNumberOfBytesRead
    mov qword [rsp+32], 0       ; lpOverlapped = NULL
    call ReadFile
    
    mov rcx, [h_file]
    call CloseHandle
    
file_error:
    mov rsp, rbp
    pop rbp
    ret


; ============================================================================
; 9. МАКРОСЫ И ПРЕПРОЦЕССОР NASM
; ============================================================================

; --- ОПРЕДЕЛЕНИЕ КОНСТАНТ ---
%define VERSION 1
%define MAX_SIZE 1024

; --- МАКРОСЫ ---
%macro print_string 1           ; макрос с 1 параметром
    lea rdx, [%1]
    mov r8, %1_len
    ; ... остальной код вывода
%endmacro

%macro save_registers 0         ; макрос без параметров
    push rax
    push rbx
    push rcx
    push rdx
%endmacro

%macro restore_registers 0
    pop rdx
    pop rcx
    pop rbx
    pop rax
%endmacro

; --- УСЛОВНАЯ КОМПИЛЯЦИЯ ---
%ifdef DEBUG
    ; код для отладки
%else
    ; код для релиза
%endif

%if VERSION > 1
    ; новый код
%elif VERSION == 1
    ; старый код
%else
    ; ещё более старый код
%endif

; --- ВКЛЮЧЕНИЕ ДРУГИХ ФАЙЛОВ ---
; %include "other_file.asm"


; ============================================================================
; 10. ОПТИМИЗАЦИЯ И ЛУЧШИЕ ПРАКТИКИ
; ============================================================================

optimization_tips:
    ; 1. Используйте регистры вместо памяти где возможно
    ; ПЛОХО:
    mov [var], 5
    add [var], 10
    
    ; ХОРОШО:
    mov rax, [var]
    add rax, 10
    mov [var], rax
    
    ; 2. Используйте LEA для арифметики
    ; вместо:
    mov rax, rbx
    add rax, rcx
    ; используйте:
    lea rax, [rbx + rcx]
    
    ; LEA может делать сложение и умножение за одну инструкцию:
    lea rax, [rbx + rcx*4 + 8]  ; RAX = RBX + RCX*4 + 8
    
    ; 3. Обнуление регистра
    ; МЕДЛЕННО:
    mov rax, 0
    ; БЫСТРО:
    xor rax, rax
    
    ; 4. Используйте INC/DEC вместо ADD/SUB для +1/-1
    inc rax         ; быстрее чем add rax, 1
    
    ; 5. Выравнивание данных для производительности
    align 16        ; выровнять на границу 16 байт
    
    ; 6. Избегайте переключения контекста между целыми и float
    ; разделяйте целочисленный и вещественный код
    
    ret


; ============================================================================
; 11. РАБОТА С ПЛАВАЮЩЕЙ ТОЧКОЙ (SSE/AVX)
; ============================================================================

section .data
    float_a dd 3.14         ; single precision (32-бит)
    double_b dq 2.71828     ; double precision (64-бит)

section .text

float_operations:
    ; SSE инструкции используют XMM регистры (xmm0-xmm15)
    
    movss xmm0, [float_a]       ; загрузить single float
    movsd xmm1, [double_b]      ; загрузить double float
    
    addss xmm0, xmm1            ; сложение single precision
    addsd xmm0, xmm1            ; сложение double precision
    
    subss xmm0, xmm1            ; вычитание
    mulss xmm0, xmm1            ; умножение
    divss xmm0, xmm1            ; деление
    
    sqrtss xmm0, xmm1           ; квадратный корень
    
    ; Сравнение float
    comiss xmm0, xmm1           ; сравнение и установка флагов
    
    ret


; ============================================================================
; 12. ОТЛАДКА
; ============================================================================

; --- ТОЧКИ ОСТАНОВА (BREAKPOINTS) ---
debugging:
    int 3               ; программная точка останова (0xCC)
    
    ; Можно использовать nop для выравнивания или временного кода:
    nop                 ; no operation
    
    ret


; ============================================================================
; 13. КОМПИЛЯЦИЯ И СБОРКА
; ============================================================================

; --- КОМАНДЫ ДЛЯ СБОРКИ ---
; 
; 1. Ассемблирование (создание объектного файла):
;    nasm -f win64 program.asm -o program.obj
;
; 2. Линковка с использованием MSVC linker:
;    link program.obj /SUBSYSTEM:CONSOLE /ENTRY:main /OUT:program.exe ^
;         kernel32.lib user32.lib
;
; 3. Или с GCC (если используется MinGW):
;    gcc program.obj -o program.exe
;
; 4. Ассемблирование с отладочной информацией:
;    nasm -f win64 -g -F cv8 program.asm -o program.obj
;
; 5. Создание листинга:
;    nasm -f win64 -l program.lst program.asm


; ============================================================================
; 14. ПРИМЕР ПОЛНОЙ ПРОГРАММЫ
; ============================================================================

section .data
    prompt db 'Enter your name: ', 0
    prompt_len equ $ - prompt
    
    greeting db 'Hello, ', 0
    greeting_len equ $ - greeting
    
    newline db 13, 10, 0

section .bss
    name_buffer resb 64
    name_length resq 1

section .text
global _start

_start:
    push rbp
    mov rbp, rsp
    sub rsp, 32
    
    ; Получить дескриптор stdout
    mov rcx, STD_OUTPUT_HANDLE
    call GetStdHandle
    mov [h_stdout], rax
    
    ; Вывести приглашение
    mov rcx, [h_stdout]
    lea rdx, [prompt]
    mov r8, prompt_len
    lea r9, [bytes_written]
    mov qword [rsp+32], 0
    call WriteConsoleA
    
    ; Получить дескриптор stdin
    mov rcx, STD_INPUT_HANDLE
    call GetStdHandle
    
    ; Прочитать имя
    mov rcx, rax            ; handle stdin
    lea rdx, [name_buffer]
    mov r8, 64
    lea r9, [name_length]
    mov qword [rsp+32], 0
    call ReadConsoleA
    
    ; Вывести приветствие
    mov rcx, [h_stdout]
    lea rdx, [greeting]
    mov r8, greeting_len
    lea r9, [bytes_written]
    mov qword [rsp+32], 0
    call WriteConsoleA
    
    ; Вывести имя
    mov rcx, [h_stdout]
    lea rdx, [name_buffer]
    mov r8, [name_length]
    lea r9, [bytes_written]
    mov qword [rsp+32], 0
    call WriteConsoleA
    
    ; Выход
    xor rcx, rcx
    call ExitProcess


; ============================================================================
; КОНЕЦ ПАМЯТКИ
; ============================================================================
; 
; ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ:
; - Intel Software Developer Manuals (официальная документация процессоров)
; - NASM Documentation: https://nasm.us/doc/
; - Windows API Documentation: https://docs.microsoft.com/windows/win32/api/
; - Agner Fog's optimization manuals: https://agner.org/optimize/
; 
; ВАЖНЫЕ ЗАМЕЧАНИЯ:
; - Всегда выравнивайте стек на 16 байт перед вызовом функций
; - Выделяйте shadow space (32 байта) перед вызовом WinAPI
; - Сохраняйте регистры RBX, RBP, RDI, RSI, R12-R15 в своих функциях
; - Проверяйте возвращаемые значения функций на ошибки
; - Используйте отладчик (x64dbg, WinDbg, VS Debugger) для анализа
; 
; ============================================================================
