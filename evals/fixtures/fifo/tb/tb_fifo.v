// Sindri P1.6 FIFO engineering seed v1 -- directed, self-checking, 4-state STRICT testbench.
// Status: engineering-seed-approved; certification: UNCERTIFIED (see ../README.md).
//
// Result protocol (F7; consumed by tests/eda/_protocol.py, later by the P1.4 adapter):
//   * one line "TEST <TestId> PASS|FAIL" per test in this configuration's inventory (tests.json),
//   * exactly one terminal line "RESULT PASS|FAIL",
//   * $finish after RESULT PASS and after RESULT FAIL alike: the process exit code is never the
//     semantic oracle (no $fatal, which is SystemVerilog; the seed is Verilog-2005).
// F7 gives completeness/consistency, NOT provenance: a candidate that prints the expected
// transcript itself would spoof a stdout-only parser (closed later in P1.4/P1.7).
// Every check is 4-state strict: a condition that is X/Z counts as a failure (probe P7).
`timescale 1ns/1ps
module tb;
  parameter WIDTH = 8;
  parameter DEPTH = 4;

  reg              clk = 1'b0;
  reg              rst = 1'b1;
  reg              in_valid = 1'b0;
  reg              out_ready = 1'b0;
  reg  [WIDTH-1:0] in_data = {WIDTH{1'b0}};
  wire             in_ready, out_valid, full, empty;
  wire [WIDTH-1:0] out_data;

  fifo #(.WIDTH(WIDTH), .DEPTH(DEPTH)) dut (
    .clk(clk), .rst(rst), .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data),
    .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .full(full), .empty(empty)
  );

  always #5 clk = ~clk;

  // Reference queue model, updated from the handshakes seen at each rising edge.
  reg [WIDTH-1:0] model [0:255];
  integer head = 0, tail = 0, errors = 0, test_errors = 0, i;
  reg     [15:0] lfsr;

  always @(posedge clk) if (!rst) begin
    if (in_valid && in_ready) begin model[tail % 256] = in_data; tail = tail + 1; end
    if (out_valid && out_ready) head = head + 1;
  end

  task check(input [8*32-1:0] what, input cond);
    if (cond !== 1'b1) begin
      errors = errors + 1; test_errors = test_errors + 1;
      $display("CHECK_FAIL t=%0t %0s occupancy=%0d out_valid=%b out_data=%h full=%b empty=%b",
               $time, what, tail - head, out_valid, out_data, full, empty);
    end
  endtask

  // Drive one cycle: apply inputs, check every visible output against the model, take the edge.
  task step(input iv, input [WIDTH-1:0] d, input ordy);
    begin
      in_valid = iv; in_data = d; out_ready = ordy; #1;
      check("empty matches model", empty === (tail == head));
      check("full matches model", full === (tail - head == DEPTH));
      check("in_ready == !full", in_ready === !full);
      check("out_valid == !empty", out_valid === !empty);
      if (out_valid === 1'b1) check("out_data is oldest word", out_data === model[head % 256]);
      @(posedge clk); #1;
    end
  endtask

  task start_test; test_errors = 0; endtask
  task end_test(input [8*32-1:0] id);
    $display("TEST %0s %0s", id, (test_errors == 0) ? "PASS" : "FAIL");
  endtask
  task do_reset;
    begin
      rst = 1'b1; in_valid = 1'b0; out_ready = 1'b0;
      @(posedge clk); @(posedge clk); #1;   // reset held across >= 1 rising edge (F2)
      rst = 1'b0; head = 0; tail = 0;
    end
  endtask

  initial begin
    start_test; do_reset;                                                     // R01
    check("reset: empty", empty === 1'b1);   check("reset: not full", full === 1'b0);
    check("reset: out_valid=0", out_valid === 1'b0); check("reset: in_ready=1", in_ready === 1'b1);
    end_test("reset_state");

    start_test; for (i = 0; i < DEPTH; i = i + 1) step(1, 8'hA0 + i, 0); step(0, 0, 0);
    end_test("fill_to_full");                                                 // R02 R03 R04

    start_test; step(1, 8'hEE, 0); step(1, 8'hEF, 0); step(0, 0, 0);
    end_test("overflow_ignored");                                             // R05

    start_test; step(0, 0, 0); step(0, 0, 0);
    end_test("stable_while_stalled");                                         // R08

    start_test; step(1, 8'h55, 1); step(0, 0, 0);
    end_test("full_push_with_pop");                                           // R05 (F3)

    start_test; for (i = 0; i < DEPTH + 1; i = i + 1) step(0, 0, 1); step(0, 0, 0);
    end_test("drain_to_empty");                                               // R03 R04

    start_test; step(0, 0, 1); step(0, 0, 1); step(0, 0, 0);
    end_test("underflow_ignored");                                            // R06

    if (DEPTH > 1) begin   // R07 is inapplicable at DEPTH == 1 (tests.json omits it there)
      start_test; step(1, 8'h11, 0); step(1, 8'h22, 1); step(1, 8'h33, 1);
      step(0, 0, 1); step(0, 0, 1); step(0, 0, 0);
      end_test("simultaneous_push_pop");                                      // R07
    end

    start_test;                                                               // R09
    in_valid = 1; in_data = 8'h3C; out_ready = 1; #1;
    check("no fall-through: out_valid=0 before edge", out_valid === 1'b0);
    @(posedge clk); #1; in_valid = 0; out_ready = 0; #1;
    check("visible after edge", out_valid === 1'b1);
    check("visible data", out_data === model[head % 256]);
    step(0, 0, 1); step(0, 0, 0);
    end_test("no_fall_through");

    start_test; step(1, 8'h77, 0); do_reset;                                  // R01
    check("mid-reset: empty", empty === 1'b1); check("mid-reset: out_valid=0", out_valid === 1'b0);
    step(1, 8'h78, 0); step(0, 0, 1); step(0, 0, 0);
    end_test("mid_reset");

    start_test; lfsr = 16'hACE1;                                              // R02 R03 R04
    for (i = 0; i < 200; i = i + 1) begin
      lfsr = {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
      step(lfsr[0], lfsr[15:8], lfsr[1]);
    end
    end_test("lfsr_stream");

    $display("SUMMARY failed_checks=%0d", errors);
    $display("RESULT %0s", (errors == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
