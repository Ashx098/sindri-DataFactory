// Sindri P1.6 FIFO engineering seed v1 -- alternate-correct implementation.
// Independent structure: explicit full/empty flag registers, no occupancy counter.
// Status: engineering-seed-approved; certification: UNCERTIFIED (see ../README.md).
`timescale 1ns/1ps
module fifo #(
  parameter WIDTH = 8,
  parameter DEPTH = 4
) (
  input  wire             clk,
  input  wire             rst,
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

  reg [WIDTH-1:0] store [0:DEPTH-1];
  reg [AW-1:0]    head;   // next word to read
  reg [AW-1:0]    tail;   // next slot to write
  reg             full_q;
  reg             empty_q;

  wire do_wr = in_valid & ~full_q;
  wire do_rd = out_ready & ~empty_q;

  function [AW-1:0] nxt;
    input [AW-1:0] p;
    nxt = (p == DEPTH-1) ? {AW{1'b0}} : p + 1'b1;
  endfunction

  assign in_ready  = ~full_q;
  assign out_valid = ~empty_q;
  assign full      = full_q;
  assign empty     = empty_q;
  assign out_data  = store[head];

  always @(posedge clk) begin
    if (rst) begin
      head    <= 0;
      tail    <= 0;
      full_q  <= 1'b0;
      empty_q <= 1'b1;
    end else begin
      if (do_wr) begin
        store[tail] <= in_data;
        tail <= nxt(tail);
      end
      if (do_rd)
        head <= nxt(head);
      case ({do_wr, do_rd})
        2'b10: begin empty_q <= 1'b0; full_q  <= (nxt(tail) == head); end
        2'b01: begin full_q  <= 1'b0; empty_q <= (nxt(head) == tail); end
        default: ;  // none, or simultaneous write+read: occupancy unchanged
      endcase
    end
  end
endmodule
