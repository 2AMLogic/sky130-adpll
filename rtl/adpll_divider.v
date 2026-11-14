// Integer-N feedback divider (spec row 5: N = 4..20; Fallback fixed N = 4).
// fb_clk is high for the first N/2 (rounded down) cycles of every N dco_clk
// cycles, so its period is exactly N dco_clk cycles and its rising edge
// lines up with count == 0.
`timescale 1ns/1ps
`default_nettype none
module adpll_divider #(
    parameter N_W = 5
) (
    input  wire           dco_clk,
    input  wire           rst_n,
    input  wire [N_W-1:0] n,       // division ratio, >= 2; held stable
    output reg            fb_clk
);
    reg [N_W-1:0] count;
    wire [N_W-1:0] last = n - 1'b1;
    wire [N_W-1:0] cnt_next = (count >= last) ? {N_W{1'b0}} : count + 1'b1;

    always @(posedge dco_clk) begin
        if (!rst_n) begin
            count  <= {N_W{1'b0}};
            fb_clk <= 1'b1;  // consistent with count == 0 (n >= 2)
        end else begin
            count  <= cnt_next;
            fb_clk <= (cnt_next < (n >> 1));
        end
    end
endmodule
`default_nettype wire
