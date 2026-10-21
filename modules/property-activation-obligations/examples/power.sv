// One boolean drain-before-power-off obligation, not a complete power model.
`define SUBJECT power_subject
`define DECOY decoy_power_subject
`define MODE power_down
`define EVENT power_off_req
`define CONDITION drained
`include "composition.vh"
