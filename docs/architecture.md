# Architecture

One canonical normalized model feeds solver adapters.

source evidence -> ingestion/provenance -> canonical model -> pre-solve QA
-> OpenSees (primary) / PyNite / Frame3DD / XC / CalculiX / native benchmarks
-> normalized results -> cross-engine validation -> SAR renderer

If an engine cannot represent a canonical feature, mark the comparison NOT_COMPARABLE; never distort the canonical model to force agreement.
