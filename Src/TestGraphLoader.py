from GraphLoader import LoadGraph
from Preprocessing import TextProcessing
print(TextProcessing("how many products were sold"))
print(TextProcessing("Sales SalesOrderDetail OrderQty ProductID"))

Graph = LoadGraph()
Node = "concept:Sales Volume"

for U, V, Data in Graph.edges(Node, data=True):
    if Data.get("relation") == "represented_by":
        print(V, Data)