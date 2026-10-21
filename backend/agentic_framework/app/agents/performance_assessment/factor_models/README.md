This folder contains the evaluation factor models used by the Performance Assessment Agent to compute individual student contributions in software engineering projects.

## Start here

- [ARCHITECTURE.md](ARCHITECTURE.md): how the agent, the cleaning and the models fit together, the evidence contract, what each factor
  cleans, how to rebuild the training data, and what is still to be built for the agent.
- `evidence/`: the shared contract and line-level cleaning. `<NN_factor>/cleaning.py`: each factor's own cleaning and features.