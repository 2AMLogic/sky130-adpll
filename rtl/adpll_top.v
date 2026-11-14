// ADPLL top level (integer-N). The phase detector is NOT in this module:
// its choice (TDC vs bang-bang) waits on decision record 0002 under the
// Proposed spec, so the boundary is explicit ports. PENDING 0002: the PD
// RTL/netlist is not provided; a PD drives pd_err/pd_valid from ref_clk and
// fb_clk, and the DCO consumes coarse/fine. Spec numbers are provisional.
`timescale 1ns/1ps
`default_nettype none
module adpll_top #(
    parameter ERR_W    = 9,
    parameter N_W      = 5,
    parameter KP_SHIFT = 3,
    parameter KI_SHIFT = 9
) (
    input  wire             ref_clk,
    input  wire             dco_clk,    // feedback from the DCO
    input  wire             rst_n,
    input  wire [N_W-1:0]   n,          // 4..20 (row 5)
    // phase-detector boundary
    output wire             fb_clk,     // divided DCO clock to the PD
    input  wire [ERR_W-1:0] pd_err,     // signed phase error, TDC LSB
    input  wire             pd_valid,   // one pulse per ref_clk result
    // DCO boundary
    output wire [5:0]       dco_coarse,
    output wire [5:0]       dco_fine,
    output wire             lock
);
    wire [13:0] code;

    adpll_divider #(.N_W(N_W)) u_div (
        .dco_clk(dco_clk), .rst_n(rst_n), .n(n), .fb_clk(fb_clk));

    adpll_loop_filter #(.ERR_W(ERR_W), .KP_SHIFT(KP_SHIFT), .KI_SHIFT(KI_SHIFT)) u_lf (
        .clk(ref_clk), .rst_n(rst_n), .en(pd_valid), .err(pd_err), .code(code));

    adpll_dco_code u_code (
        .clk(ref_clk), .rst_n(rst_n), .code(code),
        .coarse(dco_coarse), .fine(dco_fine));

    adpll_lock_detect #(.ERR_W(ERR_W)) u_lock (
        .clk(ref_clk), .rst_n(rst_n), .en(pd_valid), .err(pd_err), .lock(lock));
endmodule
`default_nettype wire
