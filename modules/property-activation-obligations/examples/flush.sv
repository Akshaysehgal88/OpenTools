// One boolean cancellation-before-flush obligation, not a transaction protocol.
`define SUBJECT flush_subject
`define DECOY decoy_flush_subject
`define MODE flushing
`define EVENT flush_req
`define CONDITION cancellation_complete
`include "composition.vh"
