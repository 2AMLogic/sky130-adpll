// Digital PI loop filter (spec row 8, 8a).
// code = MID + (err >>> KP_SHIFT) + (integ >>> KI_SHIFT); integ += err.
// Kp = 2^-KP_SHIFT, Ki = 2^-KI_SHIFT. PROVISIONAL: widths are the Proposed
// spec's initial values and the shifts are placeholders until open item O4
// (behavioural loop model) sets them. Any change is a spec change.
`timescale 1ns/1ps
`default_nettype none
module adpll_loop_filter #(
    parameter ERR_W    = 9,   // provisional: spec row 8a
    parameter INT_W    = 24,  // provisional: spec row 8a
    parameter CODE_W   = 14,  // 12 b DCO code + 2 b dither fraction
    parameter KP_SHIFT = 3,   // provisional: set by O4
    parameter KI_SHIFT = 9    // provisional: set by O4
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    en,    // one pulse per phase-detector result
    input  wire [ERR_W-1:0]        err,   // signed two's complement
    output reg  [CODE_W-1:0]       code   // unsigned, mid-code after reset
);
    localparam W = 32;
    localparam signed [W-1:0] MID  = 32'sd1 <<< (CODE_W - 1);
    localparam signed [W-1:0] CMAX = (32'sd1 <<< CODE_W) - 32'sd1;
    localparam signed [INT_W-1:0] IMAX = {1'b0, {(INT_W-1){1'b1}}};
    localparam signed [INT_W-1:0] IMIN = {1'b1, {(INT_W-1){1'b0}}};

    reg  signed [INT_W-1:0] integ;
    wire signed [W-1:0] err_x   = {{(W-ERR_W){err[ERR_W-1]}}, err};
    wire signed [W-1:0] integ_x = {{(W-INT_W){integ[INT_W-1]}}, integ};

    // Integrator update, saturating at +/- full scale (W is wide enough that
    // the sum cannot wrap before the clamp).
    wire signed [W-1:0] isum = integ_x + err_x;
    // Concatenations are unsigned, so sign-extend into signed wires before
    // comparing.
    wire signed [W-1:0] imax_x = {{(W-INT_W){IMAX[INT_W-1]}}, IMAX};
    wire signed [W-1:0] imin_x = {{(W-INT_W){IMIN[INT_W-1]}}, IMIN};
    wire signed [INT_W-1:0] inext =
        (isum > imax_x) ? IMAX :
        (isum < imin_x) ? IMIN :
        isum[INT_W-1:0];

    wire signed [W-1:0] raw = MID + (err_x >>> KP_SHIFT) + (integ_x >>> KI_SHIFT);
    wire [CODE_W-1:0] raw_clamped =
        (raw < 0)     ? {CODE_W{1'b0}} :
        (raw > CMAX)  ? {CODE_W{1'b1}} :
        raw[CODE_W-1:0];

    always @(posedge clk) begin
        if (!rst_n) begin
            integ <= {INT_W{1'b0}};
            code  <= MID[CODE_W-1:0];
        end else if (en) begin
            integ <= inext;
            code  <= raw_clamped;
        end
    end
endmodule
`default_nettype wire
