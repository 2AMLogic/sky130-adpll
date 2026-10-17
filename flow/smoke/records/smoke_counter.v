module smoke_counter (clk,
    rst_n,
    q);
 input clk;
 input rst_n;
 output [3:0] q;

 wire _00_;
 wire _01_;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;
 wire [0:0] _02_;
 wire [3:0] _03_;

 sky130_fd_sc_hd__nand2_1 _04_ (.A(q[0]),
    .B(q[1]),
    .Y(_01_));
 sky130_fd_sc_hd__xnor2_1 _05_ (.A(q[2]),
    .B(_01_),
    .Y(_03_[2]));
 sky130_fd_sc_hd__nand3_2 _06_ (.A(q[0]),
    .B(q[1]),
    .C(q[2]),
    .Y(_00_));
 sky130_fd_sc_hd__xnor2_1 _07_ (.A(q[3]),
    .B(_00_),
    .Y(_03_[3]));
 sky130_fd_sc_hd__xor2_1 _08_ (.A(q[0]),
    .B(q[1]),
    .X(_03_[1]));
 sky130_fd_sc_hd__inv_1 _09_ (.A(q[0]),
    .Y(_02_[0]));
 sky130_fd_sc_hd__dfrtp_1 _10_ (.CLK(clknet_1_0__leaf_clk),
    .D(_02_[0]),
    .RESET_B(rst_n),
    .Q(q[0]));
 sky130_fd_sc_hd__dfrtp_1 _11_ (.CLK(clknet_1_0__leaf_clk),
    .D(_03_[1]),
    .RESET_B(rst_n),
    .Q(q[1]));
 sky130_fd_sc_hd__dfrtp_1 _12_ (.CLK(clknet_1_1__leaf_clk),
    .D(_03_[2]),
    .RESET_B(rst_n),
    .Q(q[2]));
 sky130_fd_sc_hd__dfrtp_1 _13_ (.CLK(clknet_1_1__leaf_clk),
    .D(_03_[3]),
    .RESET_B(rst_n),
    .Q(q[3]));
 sky130_fd_sc_hd__buf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .X(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .X(clknet_1_1__leaf_clk));
endmodule
