# Project context and sources

## Catalyst

[Agent Fabric: A2A-T Runtime — Phase III, C26.0.910](https://www.tmforum.org/catalysts/projects/C26.0.910/agent-fabric-a2at-runtime-phase-iii) brings operators and vendors together around agent interoperability and governed telecom operations. The public project page identifies Almadar Aljadid as a champion and describes three high-value scenarios: cross-domain fault resolution, enterprise complaint handling and enterprise service fulfilment.

The repository focuses on the third scenario. It is intended as a practical companion to a CV: a reviewer can inspect a concrete service process, run its decision paths, and see how agent handoffs retain operator constraints.

## Source-to-implementation mapping

| Source | What it informed | How it is used here |
| --- | --- | --- |
| Public Catalyst project page | Project identity, Almadar participation and three HVS scenarios | Linked as the authoritative project reference |
| Team use-case development deck, `UCv3 Kevin -clean.pptx`, slides 3, 5 and 9 | Almadar fulfilment scope; access readiness, external identity and access-provider roles | Original scenario documentation; deck is not redistributed |
| Team project architecture and main presentation | Registry, task constraints, governance, operator playbooks and decision evidence | Simplified local components; no production or conformance claims |
| Colleague's project showcase webpage | Project framing and explanation of the three HVS scenarios | Context only; page, artwork and assets are not copied |
| [OpenAN](https://openan.dev/) | Open runtime direction and component boundaries | Integration reference; no dependency on its runtime |
| [OpenAN Python SDK](https://github.com/project-openan/a2a-t-sdk-python) | SDK scope and future transport integration | Linked; its code is not vendored |
| [A2A telecom extension proposal #1796](https://github.com/a2aproject/A2A/issues/1796) | Task metadata, notification and negotiation concepts | Local illustrative contracts, explicitly separate from the proposal schemas |

Internal drafts describe evolving responsibilities and proposed mechanisms. Those are background context, not definitive standards or evidence of deployed Almadar systems. The fulfilment parameters, inventory, costs, agent scores and customer are synthetic choices made for this implementation.

## Repository boundary

The original team folder is kept outside this Git repository. Meeting minutes, vendor folders, working decks, contact lists and source reports are not included. Shared Catalyst contributions remain credited to the team. The implementation demonstrates an adapted workflow; it does not claim ownership of the Catalyst platform or assert deployment on Almadar's network.
