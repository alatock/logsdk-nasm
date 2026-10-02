; NASM x64 generated directly from execute.lbc.txt
; Build: nasm -f win64 main.asm -o main.obj && gcc main.obj -o main.exe

default rel
global main
extern ExitProcess
extern printf
extern scanf
extern putchar
extern CreateProcessA
extern WaitForSingleObject
extern CloseHandle

section .data
    fmt_int db "%lld", 0
    fmt_char db "%c", 0
    msg_ram_oob db "RAM out of bounds", 10, 0
    msg_exec_error db "Cannot start external EXE", 10, 0
    exe_1 db 0x43, 0x3A, 0x2F, 0x55, 0x73, 0x65, 0x72, 0x73, 0x2F, 0x41, 0x73, 0x75, 0x73, 0x2F, 0x44, 0x65, 0x73, 0x6B, 0x74, 0x6F, 0x70, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x20, 0x6E, 0x61, 0x73, 0x6D, 0x2F, 0x6D, 0x6F, 0x64, 0x75, 0x6C, 0x65, 0x2F, 0x6C, 0x69, 0x62, 0x2E, 0x65, 0x78, 0x65, 0
    exe_args_1 db 0x22, 0x43, 0x3A, 0x2F, 0x55, 0x73, 0x65, 0x72, 0x73, 0x2F, 0x41, 0x73, 0x75, 0x73, 0x2F, 0x44, 0x65, 0x73, 0x6B, 0x74, 0x6F, 0x70, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x2F, 0x6C, 0x6F, 0x67, 0x73, 0x64, 0x6B, 0x20, 0x6E, 0x61, 0x73, 0x6D, 0x2F, 0x6D, 0x6F, 0x64, 0x75, 0x6C, 0x65, 0x2F, 0x6C, 0x69, 0x62, 0x2E, 0x65, 0x78, 0x65, 0x22, 0

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
    child_startup_info resb 104
    child_process_info resb 24

section .text
main:
    sub rsp, 88
    lea r10, [rel ram]
    mov byte [r10 + 10], 68
    mov byte [r10 + 11], 68
    mov byte [r10 + 12], 68
    mov byte [r10 + 13], 3
    lea r10, [rel ram]
    movzx rax, byte [r10 + 10]
    mov qword [rel vreg1], rax
    mov dword [rel child_startup_info], 104
    lea rcx, [rel exe_1]
    lea rdx, [rel exe_args_1]
    xor r8d, r8d
    xor r9d, r9d
    mov qword [rsp + 32], 0
    mov qword [rsp + 40], 0
    mov qword [rsp + 48], 0
    mov qword [rsp + 56], 0
    lea rax, [rel child_startup_info]
    mov qword [rsp + 64], rax
    lea rax, [rel child_process_info]
    mov qword [rsp + 72], rax
    call CreateProcessA
    test eax, eax
    jz near __exec_error_1
    mov rcx, qword [rel child_process_info]
    mov edx, 0xFFFFFFFF
    call WaitForSingleObject
    mov rcx, qword [rel child_process_info]
    call CloseHandle
    mov rcx, qword [rel child_process_info + 8]
    call CloseHandle
    jmp near __exec_done_1
__exec_error_1:
    lea rcx, [rel msg_exec_error]
    call printf
    mov ecx, 1
    call ExitProcess
__exec_done_1:
    xor ecx, ecx
    call ExitProcess
__return:
    add rsp, 88
    xor eax, eax
    ret

__ram_oob:
    lea rcx, [rel msg_ram_oob]
    call printf
    mov ecx, 1
    call ExitProcess
    ud2


