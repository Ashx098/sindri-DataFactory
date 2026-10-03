# Dependency Graph

```text
B0.G
  |
 P1.1
 / |  \
P1.2 P1.3 P1.6
  |    |    |
 P1.5 P1.4  |
   \   /   /
    P1.7
      |
    P1.8 -> P1.G

P1.G -> P2 + only explicitly dependency-ready P3/P4 work
P2.G -> full P3 qualification
P3.G + mutation assets -> P4.G
P4.G -> P5 deciding experiment
P5.G -> P6 RL entry
```

Parallelize only across clean artifact boundaries with frozen schemas. Never have two agents concurrently redefine the same schema, controller transition set, or acceptance policy without an explicit integrator.
