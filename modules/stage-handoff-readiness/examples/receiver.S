# Bare x86-64 receiver for an owned instruction-emulation readiness experiment.
# Build with --defsym VALUE=90 or VALUE=165; the caller supplies RSP and RDI.
.section .text
.global _start
_start:
    pushq $VALUE
    popq %rax
    movq %rax, (%rdi)
    hlt
.section .note.GNU-stack,"",@progbits
