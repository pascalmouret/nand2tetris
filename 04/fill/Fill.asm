// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

	@R0
	M=0
	@SCREEN
	D=A
	@8192
	D=D+A
	@screen_max
	M=D
(RESET)
	@R0
	D=M
	@color
	M=D
	@SCREEN
	D=A
	@screen_pos
	M=D-1 // since we start with +1 when painting
(LOOP)
	// set current color
	@KBD
	D=M
	@BODY
	D;JEQ
	D=1
(BODY)
	@R0
	M=D
	// check if we need to reset
	@color
	D=D-M
	@RESET
	D;JNE
	// check if we need to paint
	@screen_max
	D=M
	@screen_pos
	D=D-M
	@LOOP
	D;JEQ
	@color
	D=M
	@PAINT
	D;JEQ
	D=-1
(PAINT)
	@screen_pos
	M=M+1
	A=M
	M=D
	@LOOP
	0;JMP
	