import os
import re
import sys
from crewai import Agent, Task, Crew, Process, LLM
import litellm
from app.agents.tools.chroma_tool import create_secure_search_tool
from app.agents.tools.html_tool import convert_markdown_to_html, render_markdown_to_html
from app.core.config import settings

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf_8'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

litellm.drop_params = True


def run_marketing_planner(goal: str, org_id: int) -> str:
    openrouter_key = settings.OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY", "")
    groq_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")

    if not openrouter_key and not groq_key:
        raise ValueError(
            "Missing AI API key. Please configure OPENROUTER_API_KEY or GROQ_API_KEY in backend/.env"
        )

    # Directly query the tenant's knowledge base context deterministically
    # (Avoids CrewAI function-calling schema mismatch across third-party providers)
    search_tool = create_secure_search_tool(org_id=org_id)
    try:
        rag_context = search_tool.run(goal)
    except Exception:
        rag_context = "No specific organizational documents found."

    # Use OpenRouter as primary provider (fast, reliable, generous rate limits)
    if openrouter_key:
        primary_llm = LLM(
            model=settings.OPENROUTER_MODEL,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.3,
        )
        planning_llm = LLM(
            model=settings.OPENROUTER_MODEL,
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
        )
    else:
        primary_llm = LLM(
            model="groq/qwen/qwen3.8-27b",
            api_key=groq_key,
            temperature=0.3,
        )
        planning_llm = LLM(
            model="groq/qwen/qwen3.8-27b",
            api_key=groq_key,
            temperature=0.7,
        )

    # --- AGENTS ---
    strategist = Agent(
        role="Senior Marketing Strategist",
        goal="Formulate a high-level strategic marketing approach based on the campaign goal and context.",
        backstory="An expert marketing strategist who develops winning positioning and high-impact launch frameworks.",
        verbose=False,
        allow_delegation=False,
        llm=primary_llm,
    )

    scheduler = Agent(
        role="Execution Planner",
        goal="Translate the strategic approach into a detailed, week-by-week actionable marketing schedule.",
        backstory="A meticulous project manager who creates granular, step-by-step marketing execution plans.",
        verbose=False,
        allow_delegation=False,
        llm=planning_llm,
    )

    publisher = Agent(
        role="Content Publisher",
        goal="Transform the execution schedule into clean, semantic, web-ready HTML.",
        backstory="A web publishing specialist who formats marketing documents into semantic HTML articles.",
        verbose=False,
        allow_delegation=False,
        llm=primary_llm,
    )

    # --- TASKS ---
    analysis_task = Task(
        description=(
            f"Campaign Goal: {goal}\n\n"
            f"Knowledge Base Context: {rag_context}\n\n"
            "Formulate a structured 3-point strategic marketing framework for this campaign. "
            "Address target audience, key messaging, and competitive positioning."
        ),
        expected_output="A structured 3-point marketing strategy.",
        agent=strategist,
    )

    scheduling_task = Task(
        description=(
            "Take the strategy from the Strategist and create a comprehensive week-by-week execution schedule. "
            "Write this entirely in standard Markdown format with clear headings, daily/weekly action items, channels, and deliverables."
        ),
        expected_output="A detailed marketing execution schedule in Markdown format.",
        agent=scheduler,
    )

    formatting_task = Task(
        description=(
            "Take the execution schedule from the Execution Planner and format it into clean, semantic HTML. "
            "Structure the response inside an <article class='markdown-body'>...</article> wrapper with proper <h1>, <h2>, <h3>, <ul>, <li>, and <table> tags. "
            "Output ONLY the HTML starting with <article> and ending with </article>. Do not include conversational remarks."
        ),
        expected_output="A complete HTML article starting with <article> and ending with </article>.",
        agent=publisher,
    )

    # --- CREW ---
    crew = Crew(
        agents=[strategist, scheduler, publisher],
        tasks=[analysis_task, scheduling_task, formatting_task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    )

    result = crew.kickoff()
    raw_output = str(result.raw if hasattr(result, "raw") else result).strip()

    # Extract HTML cleanly or convert markdown deterministically
    code_block_match = re.search(
        r"```(?:html)?\s*(<article[\s\S]*?</article>)\s*```",
        raw_output,
        re.IGNORECASE,
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    if "<article" in raw_output and "</article>" in raw_output:
        start = raw_output.find("<article")
        end = raw_output.rfind("</article>") + len("</article>")
        return raw_output[start:end].strip()

    clean_markdown = re.sub(r"^```(?:markdown)?\s*", "", raw_output, flags=re.IGNORECASE)
    clean_markdown = re.sub(r"\s*```$", "", clean_markdown)
    return render_markdown_to_html(clean_markdown)
