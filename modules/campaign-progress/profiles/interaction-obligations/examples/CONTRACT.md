# Owned retained-event contract

The source and consumer share one pending bit. Initialization clears it. In the
retained mode, an event sets the bit even while the consumer is held. An existing
pending bit survives the hold and becomes visible when the consumer is released.
An acknowledgement outside the hold retires old work. A simultaneous new event
wins over that acknowledgement. Repeated events while pending otherwise coalesce.

The cold/discard mode explicitly permits the consumer hold to clear pending work.
Preservation during that hold is therefore inapplicable in this mode; event versus
acknowledgement precedence remains required outside the hold. This is the owned
fixture's specified mode, not an inferred production waiver.

Three interactions follow from that shared pending bit: arrival under hold,
pending work entering hold, and arrival with acknowledgement. Separate event and
hold tests cannot establish any of these combinations. The selected finite window
must retain native observations and enabled expected-state/delivery comparisons.
Physical reset, asynchronous delivery, arbitrary event depths and eventual-service
fairness are outside this Boolean synchronous fixture.

Interrupt/core reset and maintenance-completion/sleep use these semantics with
different native names and initialization polarity. Bug inputs deliberately seed
discard during retained hold and acknowledgement priority. They are fixture
controls, not required observation roles for the utility.
