from GraphLoader import LoadGraph

Results = []


def ReportResult(Passed: bool, Message: str) -> None:
    Results.append(Passed)
    Tag = "[PASS]" if Passed else "[FAIL]"
    print(f"{Tag} {Message}")


# 1. Basic load succeeds
Graph = None
try:
    Graph = LoadGraph()
    ReportResult(True, "Graph loaded successfully")
except Exception as E:
    ReportResult(False, f"Graph failed to load: {E}")

# 2. Node/edge counts are non-zero and sane
if Graph is not None:
    NodeCount = Graph.number_of_nodes()
    EdgeCount = Graph.number_of_edges()
    try:
        assert NodeCount > 0
        assert EdgeCount > 0
        ReportResult(True, f"Node count: {NodeCount}, Edge count: {EdgeCount}")
    except AssertionError:
        ReportResult(False, f"Node/edge counts not sane: nodes={NodeCount}, edges={EdgeCount}")
else:
    ReportResult(False, "Skipped node/edge count check - graph not loaded")

# 3. Concept nodes survived
if Graph is not None:
    ConceptNames = [N for N, D in Graph.nodes(data=True) if D.get("type") == "concept"]
    try:
        assert len(ConceptNames) > 0
        ReportResult(True, f"Concept nodes found: {len(ConceptNames)} -> {ConceptNames[:5]}")
    except AssertionError:
        ReportResult(False, f"No concept nodes found (count={len(ConceptNames)})")
else:
    ReportResult(False, "Skipped concept node check - graph not loaded")

# 4. Table nodes survived
if Graph is not None:
    TableNodes = [N for N, D in Graph.nodes(data=True) if D.get("type") != "concept"]
    try:
        assert len(TableNodes) > 0
        ReportResult(True, f"Table nodes found: {len(TableNodes)}")
    except AssertionError:
        ReportResult(False, f"No table nodes found (count={len(TableNodes)})")
else:
    ReportResult(False, "Skipped table node check - graph not loaded")

# 5. Edge attributes survived the round-trip
if Graph is not None:
    FkEdge = None
    RepresentedByEdge = None
    RelatedToEdge = None
    for _, _, D in Graph.edges(data=True):
        Relation = D.get("relation")
        if Relation is None and FkEdge is None:
            FkEdge = D
        elif Relation == "represented_by" and RepresentedByEdge is None:
            RepresentedByEdge = D
        elif Relation == "related_to" and RelatedToEdge is None:
            RelatedToEdge = D

    try:
        assert FkEdge is not None
        assert FkEdge.get("source_column")
        assert FkEdge.get("target_column")
        ReportResult(True, f"FK edge attributes intact: {FkEdge}")
    except AssertionError:
        ReportResult(False, f"FK edge attributes missing/empty: {FkEdge}")

    try:
        assert RepresentedByEdge is not None
        assert RepresentedByEdge.get("column")
        ReportResult(True, f"represented_by edge attributes intact: {RepresentedByEdge}")
    except AssertionError:
        ReportResult(False, f"represented_by edge attributes missing/empty: {RepresentedByEdge}")

    if RelatedToEdge is not None:
        print(f"  related_to edge found: {RelatedToEdge}")
    else:
        print("  No related_to edges found in graph (not necessarily an error)")
else:
    ReportResult(False, "Skipped FK edge attribute check - graph not loaded")
    ReportResult(False, "Skipped represented_by edge attribute check - graph not loaded")

# 6. Missing-file error path works correctly
try:
    LoadGraph(Path="data/does_not_exist.gpickle")
    ReportResult(False, "Missing-file error NOT raised - LoadGraph succeeded unexpectedly")
except FileNotFoundError as E:
    if "GraphBuilder.py" in str(E):
        ReportResult(True, "Missing-file error correctly raised: FileNotFoundError")
    else:
        ReportResult(False, f"FileNotFoundError raised but message doesn't mention GraphBuilder.py: {E}")
except Exception as E:
    ReportResult(False, f"Wrong exception type raised: {type(E).__name__}: {E}")

PassCount = sum(1 for R in Results if R)
print(f"\n{PassCount}/{len(Results)} checks passed")
