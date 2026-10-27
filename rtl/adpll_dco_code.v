// DCO code / dither path (spec row 8a): splits the loop-filter word
// (12 b integer + 2 b fraction) into coarse[5:0] / fine[5:0] and applies a
// first-order accumulator dither from the 2 fractional bits: the carry adds
// one fine LSB, saturating at full scale. PROVISIONAL widths per row 8a.
`timescale 1ns/1ps
`default_nettype none
module adpll_dco_code (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [13:0] code,     // {coarse[5:0], fine[5:0], frac[1:0]}
    output wire [5:0]  coarse,
    output wire [5:0]  fine
);
    wire [5:0] fine_in = code[7:2];
    wire [1:0] frac    = code[1:0];

    reg  [1:0] acc;
    wire [2:0] acc_sum = {1'b0, acc} + {1'b0, frac};
    always @(posedge clk) begin
        if (!rst_n) acc <= 2'b00;
        else        acc <= acc_sum[1:0];
    end

    assign coarse = code[13:8];
    assign fine   = (acc_sum[2] && fine_in != 6'h3f) ? fine_in + 6'd1 : fine_in;
endmodule
`default_nettype wire
