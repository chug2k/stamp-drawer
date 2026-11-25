"""Play the Stamp Drawer exercise using a scripted model and a read-only counter."""
import argparse
import json
from pathlib import Path

CARDS = json.loads(Path(__file__).with_name("cards.json").read_text(encoding="utf-8"))
TOOL = "count_rings"


def count_rings(card):
    return CARDS[card]["marks"].count("ring")


def scripted_reply(history, offered):
    question = history[0]
    if len(history) == 1:
        if TOOL not in offered:
            return {"role": "assistant", "text": "Please show me the card.", "calls": []}
        card = question["card"]
        call = {"name": TOOL, "card": card, "id": CARDS[card]["ticket"]}
        return {"role": "assistant", "text": "I'll count the rings.", "calls": [call]}

    request = history[1]["calls"][0]
    if len(history) != 3:
        raise ValueError("The outstanding request needs a tool message.")
    delivery = history[2]
    if delivery.get("role") != "tool" or delivery.get("reply_to") != request["id"]:
        raise ValueError("The result must answer the outstanding tool request.")
    return {"role": "assistant", "text": f'{request["card"]} has {delivery["value"]} rings.', "calls": []}


def play(card):
    question = {"role": "user", "card": card, "text": f"How many rings are on {card}?"}
    first = scripted_reply([question], [TOOL])
    if not first["calls"]:
        return {"scenario": "synthetic", "final_reply": first, "stopped": True}
    job = first["calls"][0]
    value = count_rings(job["card"])
    delivery = {"role": "tool", "reply_to": job["id"], "value": value}
    second = scripted_reply([question, first, delivery], [TOOL])
    assert second["calls"] == []
    return {"scenario": "synthetic", "prompt": question, "first_reply": first,
            "tool_value": value, "next_input": [question, first, delivery],
            "final_reply": second, "stopped": True}


def check():
    expected = {"Tide": 3, "Fern": 2, "Dusk": 4}
    for card, answer in expected.items():
        run = play(card)
        receipt = run["next_input"][-1]
        assert run["tool_value"] == answer
        assert receipt == {"role": "tool", "reply_to": CARDS[card]["ticket"], "value": answer}
        assert run["final_reply"]["calls"] == [] and run["stopped"]
        assert len(run["next_input"]) == 3
        prompt, first = run["next_input"][:2]
        assert scripted_reply([prompt], [])["calls"] == []
        for invalid in ([prompt, first], [prompt, first, dict(receipt, role="user")],
                        [prompt, first, dict(receipt, reply_to="different-ticket")]):
            try:
                scripted_reply(invalid, [TOOL])
            except ValueError:
                continue
            raise AssertionError("A missing or mismatched tool return was accepted.")
        print(f'{card}: {answer} rings, tool reply {receipt["reply_to"]}, 2 model turns, 1 tool, stopped')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--card", choices=list(CARDS), default="Tide")
    parser.add_argument("--check", action="store_true", help="check all cards and rejected returns")
    args = parser.parse_args()
    if args.check:
        check()
    else:
        print(json.dumps(play(args.card), indent=2))
