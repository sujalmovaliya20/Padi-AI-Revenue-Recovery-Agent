# 90-Second Hackathon Live Demo Script
## Project: Revenue Recovery Agent (LangGraph + NVIDIA NIM + Razorpay)

---

### [00:00 - 00:15] Introduction & The Problem
> **What to Say:**  
> *"Every SaaS and subscription business loses 5% to 9% of monthly recurring revenue to silent, involuntary payment failures — expired cards, bank switch outages, and mandate declines.  
> Traditional recovery is dumb: it either blasts retries blindly, burning customer goodwill, or gives up.  
> We built the **AI Revenue Recovery Agent** — a bounded, autonomous LangGraph state machine powered by NVIDIA NIM that diagnoses root causes and executes safe, policy-gated Razorpay interventions."*

---

### [00:15 - 00:35] Triggering the Live Batch & Architecture
> **What to Do:**  
> 1. Point at the clean dashboard at `http://localhost:3000`.
> 2. Click **"Run Batch (75 Records)"** in the top right.
> 3. Point at the live progress bar and status counter updating in real-time.
>
> **What to Say:**  
> *"Right now, we are feeding 75 realistic failed subscription payments across Indian merchants into our backend.  
> As you see on the live progress bar, each transaction is evaluated through our LangGraph state machine:  
> 1. First, failure reasons are classified with rule-based heuristics or NVIDIA NIM fallback.  
> 2. Next, our policy engine selects bounded recovery actions.  
> 3. Crucially, before executing any real Razorpay tool call, our **Safety Gate** enforces compliance whitelists, retry limits, and a ₹5,000 safety ceiling."*

---

### [00:35 - 00:55] KPI Metrics & Funnel Visualization
> **What to Do:**  
> 1. Point at the **KPI Summary Cards** and the **Recharts Pipeline Funnel**.
>
> **What to Say:**  
> *"Look at these live, honest metrics:  
> Out of **₹1,46,000 at risk**, the agent immediately recovered **₹6,296** on transient network switch glitches by triggering real Razorpay Order retries.  
> For expired cards, rather than failing silently, the agent generated live Razorpay payment update links (like `https://rzp.io/rzp/...`) and scheduled proactive customer link dispatches.  
> For revoked mandates, our compliance gate immediately escalated them to human CSR queues rather than making illegal auto-debits."*

---

### [00:55 - 01:15] Deep Dive into the Audit Trail
> **What to Do:**  
> 1. Scroll to the **"All Payments Audit Trail"** table.
> 2. Expand a payment row (e.g. `pay_syn_0822_1003` - Expired Card or `pay_syn_0823_1001` - Bank Decline).
> 3. Show the chronological step-by-step narrative drawer with raw Razorpay tool JSON outputs.
>
> **What to Say:**  
> *"Every single autonomous decision is completely transparent and audit-logged:  
> You can see the step sequence: Failure Detected $\rightarrow$ Classified as Expired Card $\rightarrow$ Policy Selected Payment Link $\rightarrow$ Gate Passed under ₹5,000 cap $\rightarrow$ Real Razorpay Tool Generated Link $\rightarrow$ Customer Promise Tracked.  
> No black-box hallucinations. Full enterprise explainability."*

---

### [01:15 - 01:30] The Innovation Moment: Cost-Aware Autonomous Stop Rule
> **What to Do:**  
> 1. Click on the **"Honest Exception List"** tab.
> 2. Point at the **"Cost Safeguard Stop"** badge and low-ticket items (e.g. ₹299 / ₹499 payments).
>
> **What to Say:**  
> *"Here is our core innovation: **The Cost-Aware Autonomous Stop Rule**.  
> In recurring payments, each retry attempt costs around ₹150 in gateway penalties and customer friction.  
> If an invoice is only ₹299, blindly retrying 3 times would consume more than 50% of the customer's value!  
> Our agent calculates the cumulative cost against invoice value. When retry costs exceed 30% of the invoice, the agent **autonomously halts retries** to protect merchant margins.  
> That is bounded, economically-sound AI that CFOs can trust."*

---

### Demo Checklist & Key Numbers Cheat Sheet:
- **Total Failed Payments in Batch**: `75`
- **Total Revenue at Risk**: `~₹1,46,025 INR`
- **Instant Technical Recovery**: `~₹6,296 INR` (Real Razorpay test-mode orders created)
- **High-Value Gate Cap**: `₹5,000.00`
- **Cost-Ceiling Limit**: `30% of invoice amount`
- **LLM Provider**: NVIDIA NIM (`nvidia/nemotron-3.5-lightning-30b-a3b` / `meta/llama-3.1-70b-instruct`)
- **Payment Gateway**: Razorpay Test-Mode SDK (Orders API, Payment Links API, Subscriptions API)
