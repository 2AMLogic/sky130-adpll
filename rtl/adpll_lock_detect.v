// Lock detector (spec row 9): lock asserts once |err| <= LOCK_THRESH TDC LSB
// for LOCK_CYCLES consecutive reference cycles. PROVISIONAL: LOCK_THRESH and
// LOCK_CYCLES are the Proposed spec's values; UNLOCK_THRESH (hysteresis on
// deassert) is NOT in the spec and is a placeholder pending a decision.
`timescale 1ns/1ps
`default_nettype none
module adpll_lock_detect #(
    parameter ERR_W         = 9,
    parameter LOCK_THRESH   = 4,   // provisional: spec row 9
    parameter UNLOCK_THRESH = 8,   // provisional: not in spec
    parameter LOCK_CYCLES   = 64   // provisional: spec row 9
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              en,
    input  wire [ERR_W-1:0]  err,   // signed
    output reg               lock
);
    localparam CNT_W = $clog2(LOCK_CYCLES + 1);

    wire [ERR_W-1:0] mag = err[ERR_W-1] ? (~err + 1'b1) : err;  // |err|, -256 -> 256 (9 b unsigned)
    wire in_lock   = (mag <= LOCK_THRESH[ERR_W-1:0]);
    wire out_unlock = (mag > UNLOCK_THRESH[ERR_W-1:0]);

    reg [CNT_W-1:0] run;

    always @(posedge clk) begin
        if (!rst_n) begin
            run  <= {CNT_W{1'b0}};
            lock <= 1'b0;
        end else if (en) begin
            if (in_lock) begin
                if (run == LOCK_CYCLES[CNT_W-1:0] - 1'b1) lock <= 1'b1;
                if (run != LOCK_CYCLES[CNT_W-1:0]) run <= run + 1'b1;
            end else begin
                run <= {CNT_W{1'b0}};
                if (out_unlock) lock <= 1'b0;
            end
        end
    end
endmodule
`default_nettype wire
