from langchain_core.messages import AIMessage, HumanMessage


def ask(graph, q, history=None, emp="E1001"):
    return graph.invoke({"question": q, "employee_id": emp, "history": history or []})


def test_policy_question_is_grounded_and_cited(graph):
    out = ask(graph, "How many days of paternity leave do I get?")
    assert out["route"] == "policy_question"
    assert out["context_ok"] is True
    assert "10 working days" in out["answer"]
    assert "[" in out["answer"] and out["sources"]


def test_leave_balance_uses_database_tool(graph):
    out = ask(graph, "What is my leave balance?", emp="E1002")
    assert out["route"] == "leave_balance"
    assert "6.5" in out["answer"] and "Rahul" in out["answer"]


def test_out_of_scope_question_escalates_with_ticket(graph):
    out = ask(graph, "What is the stock options vesting schedule?")
    assert out["context_ok"] is False
    assert out["ticket_id"] is not None
    assert "ticket" in out["answer"]


def test_explicit_human_request_escalates(graph):
    out = ask(graph, "I want to raise a ticket with HR")
    assert out["route"] == "escalate" and out["ticket_id"]


def test_chitchat(graph):
    assert ask(graph, "hello")["route"] == "chitchat"


def test_follow_up_is_rewritten_with_history(graph):
    history = [HumanMessage("How many sick leaves do I get?"), AIMessage("You get 12 days of sick leave [1].")]
    out = ask(graph, "Can I carry it forward?", history=history)
    assert "sick" in out["search_query"].lower()
    assert "Sick leave does not carry forward" in out["answer"]
