# verify
Catch hallucinated citations
---
$ with /make-bib, find all flaw from references.bib and correct them. ensure ALL field matches with source and write source/link as comment.
[spinner:2500] Dispatching 6 parallel agents (8 entries each)...
> [dim]Checking against DBLP, arXiv, CrossRef, publisher pages...[/dim]
[spinner:3000] Verifying 49 entries...
> [green]✓[/green] Batch 1 complete — [yellow]3 errors[/yellow]
> [green]✓[/green] Batch 2 complete — [red]3 critical errors[/red]
> [green]✓[/green] Batch 3 complete — [yellow]2 errors[/yellow]
> [green]✓[/green] Batch 4 complete — [yellow]2 errors[/yellow]
> [green]✓[/green] Batch 5 complete — [red]3 critical errors[/red]
> [green]✓[/green] Batch 6 complete — [red]1 critical error[/red]
>
> [bold][red]14 of 49 entries have errors.[/red][/bold]
>
> [red]✗[/red] [bold]kim2024openvla[/bold] — wrong venue
>   booktitle = {ICML}    [dim]← LLM wrote this[/dim]
>   booktitle = {CoRL}    [dim]← actually published here[/dim]
>
> [red]✗[/red] [bold]liu2025can[/bold] — all 8 author given names hallucinated
>   LLM:    Liu, [red]Zhecheng[/red] / Gao, [red]Zhehui[/red] / Wei, [red]Yuting[/red] ...
>   Actual: Liu, [green]Jijia[/green]    / Gao, [green]Feng[/green]   / Wei, [green]Bingwen[/green] ...
>
> [red]✗[/red] [bold]wang2025vlatest[/bold] — 4 of 6 author last names wrong
> [red]✗[/red] [bold]zhang2024vlabench[/bold] — year wrong, 7 of 8 authors fabricated
> [red]✗[/red] [bold]perez2018film[/bold] — pages 386–393, actually 3942–3951
> [red]✗[/red] [bold]wen2025tinyvla[/bold] — 5 of 13 authors missing
> [red]✗[/red] [bold]hu2022lora[/bold] — missing co-author, wrong last name
> [red]✗[/red] [bold]oxe2024[/bold] — arXiv preprint → actually ICRA 2024
> [dim]  + 6 more entries with wrong venues, titles, or keys[/dim]
>
[spinner:2000] Fixing all entries...
> [green]✓[/green] [bold]14 entries fixed. Source URLs added to all 49.[/bold]
> [green]✓[/green] 3 citation keys updated in main.tex + appendix.tex.
>
>
>
>
>
>
>
>
>
>
