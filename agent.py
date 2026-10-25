import json
import re
from typing import Dict, Any, List, Optional, Tuple
from tools import (
    extract_medicines,
    lookup_drug,
    check_interaction,
    find_generic,
    build_timeline,
    escalate
)
from sarvam_client import chat_completion, translate_text

SYSTEM_PROMPT = """You are "Dawai Dost" (दवाई दोस्त), an empathetic, highly responsible Indian AI Medical Prescription Assistant.
Your mission is to help Indian patients understand their prescription medicines clearly and safely.

SAFETY DIRECTIVES:
1. NEVER diagnose diseases or prescribe personal dosages.
2. Only state what the official medicine label usually says (e.g., "The label usually says...").
3. If a medicine involves high risk, unknown ingredients, a pregnant woman, or an infant/child, immediately invoke `escalate`.
4. Always prioritize patient safety over convenience.

AVAILABLE TOOLS:
- extract_medicines(input): Normalizes raw medicine lists into structured {name, strength, frequency, duration}.
- lookup_drug(name): Retrieves label usage, warnings, timing, purpose from standard database.
- check_interaction(drug_a, drug_b): Checks if two medicines have documented adverse interactions.
- find_generic(name): Provides generic equivalent and Jan Aushadhi Kendra cost-saving tips.
- build_timeline(medicines): Creates a Daily Medicine Timeline (Morning / Afternoon / Night).
- escalate(reason): Flags safety risk and provides helpline and doctor consultation advice.

TOOL CALL PROTOCOL:
You can reason and call tools step-by-step for up to 5 steps.
To call a tool, respond with ONLY a JSON object:
{"thought": "brief reason for calling tool", "tool": "tool_name", "args": {"arg_key": "arg_value"}}

When you have collected enough facts and are ready to answer the user, output:
{"thought": "ready to reply", "final": "Clear, friendly, polite explanation for the user with timing and purpose"}
"""

def _clean_json_str(text: str) -> str:
    """Extracts JSON substring from model output."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text

class DawaiDostAgent:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Dispatches tool execution and returns (raw_result, summary_str)."""
        if tool_name == "lookup_drug":
            name = args.get("name", "")
            res = lookup_drug(name)
            summary = f"Found: {res.get('generic_name', 'Not found')} | Timing: {res.get('timing', 'N/A')}"
            return res, summary

        elif tool_name == "check_interaction":
            a = args.get("drug_a", "")
            b = args.get("drug_b", "")
            res = check_interaction(a, b)
            summary = f"Interaction: {res.get('severity')} - {res.get('warning', 'None')[:60]}"
            return res, summary

        elif tool_name == "find_generic":
            name = args.get("name", "")
            res = find_generic(name)
            summary = f"Generic: {res.get('generic_name')} (Jan Aushadhi available)"
            return res, summary

        elif tool_name == "build_timeline":
            meds = args.get("medicines", [])
            res = build_timeline(meds)
            summary = f"Timeline built: {res.get('summary', '')}"
            return res, summary

        elif tool_name == "escalate":
            reason = args.get("reason", "Doctor consultation recommended")
            res = escalate(reason)
            summary = f"Escalated: {reason}"
            return res, summary

        elif tool_name == "extract_medicines":
            inp = args.get("input", [])
            res = extract_medicines(inp)
            summary = f"Extracted {len(res)} medicine items"
            return {"medicines": res}, summary

        else:
            return {"error": f"Unknown tool: {tool_name}"}, "Error: unknown tool"

    def run(
        self,
        user_query: str,
        medicines: Optional[List[Dict[str, Any]]] = None,
        language: str = "hi-IN"
    ) -> Dict[str, Any]:
        """
        Executes the agentic reasoning loop.
        Returns: { reply_text, tool_trace, timeline, escalated }
        """
        medicines = medicines or []
        tool_trace: List[Dict[str, Any]] = []
        escalated = False
        escalate_reason = ""
        timeline = None

        # Detect emergency or pediatric/pregnancy keywords in query
        q_lower = user_query.lower()
        if any(w in q_lower for w in ["pregnant", "pregnancy", "garbhwati", "bachha", "child", "infant", "chest pain", "severe bleeding"]):
            esc = escalate("User query mentions pregnancy, pediatric use, or critical symptoms requiring in-person diagnosis.")
            tool_trace.append({
                "step": 1,
                "tool": "escalate",
                "args": {"reason": "High risk case detected"},
                "summary": "Escalated for immediate clinical doctor consult"
            })
            escalated = True
            escalate_reason = esc["reason"]

        # Ensure timeline is generated if medicines are present
        if medicines:
            timeline_res, summary = self.execute_tool("build_timeline", {"medicines": medicines})
            timeline = timeline_res
            tool_trace.append({
                "step": len(tool_trace) + 1,
                "tool": "build_timeline",
                "args": {"medicines_count": len(medicines)},
                "summary": summary
            })

            # Check interactions between pairs if multiple medicines exist
            med_names = [m.get("name", "") for m in medicines if m.get("name")]
            for i in range(len(med_names)):
                for j in range(i + 1, len(med_names)):
                    inter_res, inter_sum = self.execute_tool("check_interaction", {"drug_a": med_names[i], "drug_b": med_names[j]})
                    if inter_res.get("has_interaction"):
                        tool_trace.append({
                            "step": len(tool_trace) + 1,
                            "tool": "check_interaction",
                            "args": {"drug_a": med_names[i], "drug_b": med_names[j]},
                            "summary": inter_sum
                        })
                        if inter_res.get("severity") == "High":
                            escalated = True
                            escalate_reason = inter_res.get("warning")

        # Multi-step Agent LLM reasoning loop with Sarvam-105B
        history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"User Query: {user_query}\n"
                    f"Prescribed Medicines: {json.dumps(medicines, ensure_ascii=False)}\n"
                    f"Target User Language: {language}\n"
                    "Think step by step and decide whether to call a tool or give the final answer."
                )
            }
        ]

        final_reply = ""
        for step_idx in range(1, self.max_steps + 1):
            try:
                model_out = chat_completion(history, temperature=0.2)
                cleaned = _clean_json_str(model_out)
                parsed = json.loads(cleaned)

                if "final" in parsed:
                    final_reply = parsed["final"]
                    break

                if "tool" in parsed:
                    tool_name = parsed["tool"]
                    args = parsed.get("args", {})
                    thought = parsed.get("thought", "")

                    res, sum_str = self.execute_tool(tool_name, args)
                    tool_trace.append({
                        "step": len(tool_trace) + 1,
                        "tool": tool_name,
                        "thought": thought,
                        "args": args,
                        "summary": sum_str
                    })

                    if tool_name == "escalate":
                        escalated = True
                        escalate_reason = args.get("reason", "Doctor consultation recommended")

                    # Feed tool result back to agent
                    history.append({"role": "assistant", "content": json.dumps(parsed)})
                    history.append({"role": "user", "content": f"Tool '{tool_name}' returned: {json.dumps(res, ensure_ascii=False)}. Next action?"})

            except Exception as e:
                # If JSON parsing or model tool loop encounters an issue, break out gracefully
                print(f"[Agent Step {step_idx} notice] {e}")
                break

        # If LLM didn't produce a final answer in the loop, generate a concise, friendly synthesis
        if not final_reply:
            synthesis_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are Dawai Dost. Explain the prescription clearly, warmly, and concisely in Hindi (or the user's requested language). "
                        "Cover each medicine: its purpose, exact timing (before/after food, morning/night), and a note about Jan Aushadhi generic savings. "
                        "Keep it direct, structured, and easy to understand when read aloud. Never diagnose or alter doses."
                    )
                },
                {"role": "user", "content": f"User asked: '{user_query}'. Medicines: {json.dumps(medicines)}. Timeline summary: {timeline.get('summary') if timeline else 'None'}."}
            ]
            try:
                final_reply = chat_completion(synthesis_prompt, temperature=0.2)
            except Exception:
                final_reply = "नमस्ते! कृपया अपनी दवाइयों को डॉक्टर के परामर्श अनुसार ही लें। सुबह और रात की दवाओं का विशेष ध्यान रखें।"

        # Translate final reply to requested Indian language only if not already in that script
        if language and language != "en-IN":
            is_already_devanagari = bool(re.search(r"[\u0900-\u097F]", final_reply))
            if not (language == "hi-IN" and is_already_devanagari):
                try:
                    translated = translate_text(final_reply, target_language_code=language, source_language_code="auto")
                    if translated and len(translated) > 10:
                        final_reply = translated
                except Exception as e:
                    print(f"[Agent Translation Error] {e}")

        # Always append escalation notice if flagged
        if escalated and escalate_reason:
            safety_banner = (
                f"\n\n⚠️ सलाह (Important): {escalate_reason} "
                "कृपया किसी भी प्रकार के संशय में अपने डॉक्टर या नजदीकी फार्मासिस्ट से तुरंत संपर्क करें।"
            )
            final_reply += safety_banner

        return {
            "reply_text": final_reply,
            "tool_trace": tool_trace,
            "timeline": timeline,
            "escalated": escalated
        }
