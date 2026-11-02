// DCO structural netlist (spec row 14: sky130_fd_sc_hd library cells only,
// no behavioural logic, no hand-drawn cell). PROVISIONAL: topology and bank
// weights are a starting structure; spec rows 2/3 (range, fine LSB) are
// graded by DCO cell SPICE, post-layout (open item O3), not by this file.
//
// Ring: 5 inverting stages (stage 0 = NAND2 enable gate, stages 1..4 = inv_2),
// so the loop has odd inversion count. Tuning, speed rises with code:
//   coarse[5:0]: bit k enables 2^k einvp_1 cells in parallel with stage 2
//   fine[5:0]  : bit k enables 2^k einvp_1 cells in parallel with stage 3,
//                one unit is a small step
// Each einvp_1 input A is the stage's input node and Z the stage output node,
// so an enabled cell adds drive in parallel with the stage inverter; a
// disabled cell still loads the node (that load is part of what SPICE grades).
// Placement-dependent: ring order and bank grouping are the placement
// constraint (spec/placement-constraints.md).
`timescale 1ns/1ps
`default_nettype none
module dco (
    input  wire       en,
    input  wire [5:0] coarse,
    input  wire [5:0] fine,
    output wire       clk_out
);
    wire [4:0] n;  // n[i] = output of stage i; ring closes n[4] -> stage 0

    sky130_fd_sc_hd__nand2_2 u_stage0 (.A(n[4]), .B(en), .Y(n[0]));
    sky130_fd_sc_hd__inv_2   u_stage1 (.A(n[0]), .Y(n[1]));
    sky130_fd_sc_hd__inv_2   u_stage2 (.A(n[1]), .Y(n[2]));
    sky130_fd_sc_hd__inv_2   u_stage3 (.A(n[2]), .Y(n[3]));
    sky130_fd_sc_hd__inv_2   u_stage4 (.A(n[3]), .Y(n[4]));

    genvar k, j;
    generate
        for (k = 0; k < 6; k = k + 1) begin : g_coarse
            for (j = 0; j < (1 << k); j = j + 1) begin : g_unit
                sky130_fd_sc_hd__einvp_1 u_c (.A(n[1]), .TE(coarse[k]), .Z(n[2]));
            end
        end
        for (k = 0; k < 6; k = k + 1) begin : g_fine
            for (j = 0; j < (1 << k); j = j + 1) begin : g_unit
                sky130_fd_sc_hd__einvp_1 u_f (.A(n[2]), .TE(fine[k]), .Z(n[3]));
            end
        end
    endgenerate

    sky130_fd_sc_hd__inv_4 u_out (.A(n[4]), .Y(clk_out));
endmodule
`default_nettype wire
