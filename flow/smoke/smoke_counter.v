// Toolchain smoke fixture (issue #3): a trivial 4-bit counter so `klt
// synthesize` and `klt place-and-route` have something real to run on
// sky130_fd_sc_hd. Not a design; no figure from it is evidence about the ADPLL.
module smoke_counter (input clk, input rst_n, output reg [3:0] q);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) q <= 4'd0;
    else        q <= q + 4'd1;
endmodule
