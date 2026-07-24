"""Abstract interface protocols for the knowledge infrastructure.

Every concrete implementation in parsers/, chunking/, and vectorstore/
must satisfy exactly one of these protocols. This enforces the single-
responsibility principle and makes each component independently testable.
"""
