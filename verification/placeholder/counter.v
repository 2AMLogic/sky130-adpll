// Placeholder DUT for the harness smoke test. NOT ADPLL RTL: it lives under
// verification/ so that rtl/ stays empty (and rtl lint vacuous) until the
// first real RTL PR.
`timescale 1ns/1ps
`default_nettype none
module counter #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             en,
    output reg  [WIDTH-1:0] count
);
    always @(posedge clk) begin
        if (!rst_n) count <= {WIDTH{1'b0}};
        else if (en) count <= count + 1'b1;
    end
endmodule
`default_nettype wire
