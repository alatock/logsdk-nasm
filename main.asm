; NASM x64 generated directly from execute.lbc.txt
; Build (MinGW): nasm -f win64 main.asm -o main.obj && gcc main.obj -o main.exe

default rel
global main
extern ExitProcess
extern printf
extern scanf
extern putchar
extern system

section .data
    fmt_int db "%lld", 0
    fmt_char db "%c", 0
    msg_ram_oob db "RAM out of bounds", 10, 0
    cmd_1 db 0x22, 0x43, 0x3A, 0x2F, 0x55, 0x73, 0x65, 0x72, 0x73, 0x2F, 0x41, 0x73, 0x75, 0x73, 0x2F, 0x44, 0x65, 0x73, 0x6B, 0x74, 0x6F, 0x70, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x20, 0x6E, 0x61, 0x73, 0x6D, 0x2F, 0x6D, 0x6F, 0x64, 0x75, 0x6C, 0x65, 0x2F, 0x6E, 0x6D, 0x6D, 0x2E, 0x65, 0x78, 0x65, 0x22, 0

section .bss
    ram resb 1048576
    vreg1 resq 1
    vreg2 resq 1
    vreg3 resq 1
    vreg4 resq 1
    vreg5 resq 1
    vreg6 resq 1
    vreg7 resq 1
    vreg8 resq 1
    vreg9 resq 1
    vreg10 resq 1
    vreg11 resq 1
    vreg12 resq 1
    vreg13 resq 1
    vreg14 resq 1
    vreg15 resq 1
    vreg16 resq 1
    input_val resq 1
    input_char resb 1

section .text
main:
    sub rsp, 40
    mov rax, 3
    mov qword [rel vreg3], rax
    mov rax, 6
    mov qword [rel vreg4], rax
    mov rax, qword [rel vreg2]
    cmp rax, 2
    jne near syn
    jmp near end
syn:
    mov rdx, qword [rel vreg3]
    lea rcx, [rel fmt_int]
    call printf
    mov ecx, 10
    call putchar
    lea rcx, [rel cmd_1]
    call system
end:
    mov rdx, qword [rel vreg4]
    lea rcx, [rel fmt_int]
    call printf
    mov ecx, 10
    call putchar
    xor ecx, ecx
    call ExitProcess
__return:
    add rsp, 40
    xor eax, eax
    ret

__ram_oob:
    lea rcx, [rel msg_ram_oob]
    call printf
    mov ecx, 1
    call ExitProcess
    ud2

