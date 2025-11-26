"""
LangGraph workflow configuration for the AI Tools.
"""

from langgraph.graph import StateGraph, END
from models import QueryState

from .agents import (
    structured_summarizer,
    planner,
    executor,
    answer_subquestions,
    synthesizer,
    evaluator,
    should_replan
)

def create_workflow_graph():
    """
    Creates and returns a compiled LangGraph workflow graph.
    """
    graph = StateGraph(QueryState)
    
    # Add nodes
    graph.add_node("summarizer", structured_summarizer)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("answer_subqs", answer_subquestions)
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("evaluator", evaluator)

    # Add edges
    graph.set_entry_point("summarizer")
    graph.add_edge("summarizer", "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "answer_subqs")
    graph.add_edge("answer_subqs", "synthesizer")
    graph.add_edge("synthesizer", "evaluator")
    graph.add_conditional_edges("evaluator", should_replan, {"end": END, "replan": "planner"})
    
    # Compile the graph
    compiled_graph = graph.compile()
    
    # Visualize the graph (optional)
    def draw_ascii(graph):
        print("Workflow ASCII Diagram:")
        for edge in graph.edges:
            print(f"{edge[0]} --> {edge[1]}")
        if hasattr(graph, 'conditional_edges'):
            for from_node, cond in graph.conditional_edges.items():
                for label, to_node in cond.items():
                    print(f"{from_node} --[{label}]--> {to_node}")
    
    # Print the graph visualization
    print(compiled_graph.get_graph().draw_ascii())
    
    return compiled_graph
