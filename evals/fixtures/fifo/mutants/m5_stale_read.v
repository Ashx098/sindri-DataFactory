// Sindri P1.6 FIFO engineering seed v1 -- MUTANT M5 (stale read data): out_data reads the previous cycle's read pointer.
// Deliberately WRONG. UNCERTIFIED seed mutant (see manifest.json); derived from rtl/fifo_ref.v.
// Status: engineering-seed-approved; certification: UNCERTIFIED (see ../README.md).
// Contract: ../contract/contract.md. Synthesizable Verilog-2005 subset (F6).
`timescale 1ns/1ps
module fifo #(
  parameter WIDTH = 8,
  parameter DEPTH = 4
) (
  input  wire             clk,
  input  wire             rst,        // synchronous, active-high (F2)
  input  wire             in_valid,
  output wire             in_ready,
  input  wire [WIDTH-1:0] in_data,
  output wire             out_valid,
  input  wire             out_ready,
  output wire [WIDTH-1:0] out_data,
  output wire             full,
  output wire             empty
);
  localparam AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;

  reg [WIDTH-1:0] mem [0:DEPTH-1];
  reg [AW-1:0]    wr_ptr;
  reg [AW-1:0]    rd_ptr;
  reg [AW:0]      count;

  wire push = in_valid && in_ready;
  wire pop  = out_valid && out_ready;

  assign full      = (count == DEPTH);
  assign empty     = (count == 0);
  assign in_ready  = !full;             // F3: no push when full, even with a same-cycle pop
  assign out_valid = !empty;            // F4: no fall-through
  reg [AW-1:0] rd_prev;
  always @(posedge clk) rd_prev <= rd_ptr;
  assign out_data  = mem[rd_prev];      // MUTANT: one cycle stale

  always @(posedge clk) begin
    if (rst) begin
      wr_ptr <= 0;
      rd_ptr <= 0;
      count  <= 0;
    end else begin
      if (push) begin
        mem[wr_ptr] <= in_data;
        wr_ptr <= (wr_ptr == DEPTH-1) ? 0 : wr_ptr + 1;
      end
      if (pop)
        rd_ptr <= (rd_ptr == DEPTH-1) ? 0 : rd_ptr + 1;
      if (push && !pop)
        count <= count + 1;
      else if (pop && !push)
        count <= count - 1;
    end
  end
endmodule
