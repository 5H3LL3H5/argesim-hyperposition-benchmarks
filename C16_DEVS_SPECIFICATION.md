# Formal DEVS Specification for ARGESIM C16

According to the classical Discrete Event System Specification (DEVS) by Zeigler et al., a system can be represented by atomic and coupled models. The ARGESIM C16 Restaurant Business Dynamics benchmark can be formally specified as a Coupled DEVS Model comprised of variable-structure Atomic DEVS Models.

## 1. Coupled DEVS Model: C16 Network

The top-level model is a Dynamic Structure DEVS (DSDEVS), as the number of restaurants changes over time.

$$ N = \langle X, Y, D, \{M_d | d \in D\}, EIC, EOC, IC \rangle $$

Where:
- $X = \emptyset$ (The overall system is closed and autonomous)
- $Y = \{ \text{status\_update} \}$ (Output of total taxes and restaurant locations)
- $D = P \cup R$ (The set of component references: $P$ for Persons, $R$ for Restaurants. $P$ is static, $|P|=3000$. $R$ is dynamic, initially $|R|=30$).
- $M_d$: The atomic model for component $d$.
- $IC$ (Internal Couplings): A person $p \in P$ is coupled to a restaurant $r \in R$ if $distance(p.pos, r.pos) \le \text{Range}$. Thus, $p.out \rightarrow r.in$.
- $EIC = \emptyset, EOC = \emptyset$

---

## 2. Atomic DEVS Model: Person ($M_p$)

A person acts as a pure autonomous generator of dining events.

$$ M_p = \langle X_p, Y_p, S_p, \delta_{int}, \delta_{ext}, \delta_{con}, \lambda, ta \rangle $$

- **Input Ports/Values ($X_p$):** $\emptyset$ (Persons do not receive events)
- **Output Ports/Values ($Y_p$):** `out` port emitting values $v = ( \text{cost} \in \mathbb{R} )$
- **State Space ($S_p$):** $S_p = \{ (\text{phase}, \sigma, x, y) \}$
  - $\text{phase} \in \{ \text{waiting} \}$
  - $\sigma \in \mathbb{R}_{0}^{+}$ (time remaining until next restaurant visit)
  - $x, y \in \mathbb{R}$ (spatial coordinates, invariant)
- **Time Advance Function ($ta$):**
  - $ta(s) = \sigma$
- **Output Function ($\lambda$):**
  - $\lambda(s):$ Randomly select a restaurant $r \in R_{range}$ uniformly. Emit `cost = DinnerCost` on the coupling to $r$.
- **Internal Transition Function ($\delta_{int}$):**
  - $\delta_{int}(s):$ Set $\sigma = \text{UniformDiscrete}(1, \text{MaximumDiningInterval})$ days.
- **External Transition Function ($\delta_{ext}$):**
  - Not applicable as $X_p = \emptyset$.
- **Confluent Transition Function ($\delta_{con}$):**
  - Not applicable.

---

## 3. Atomic DEVS Model: Restaurant ($M_r$)

A restaurant acts as an accumulator for revenue and evaluates its state periodically.

$$ M_r = \langle X_r, Y_r, S_r, \delta_{int}, \delta_{ext}, \delta_{con}, \lambda, ta \rangle $$

- **Input Ports/Values ($X_r$):** `in` port receiving values $v = ( \text{cost} \in \mathbb{R} )$ from persons.
- **Output Ports/Values ($Y_r$):** `out` port emitting values $y \in \{ \text{close}, \text{open}(x', y') \}$
- **State Space ($S_r$):** $S_r = \{ (\text{phase}, \sigma, x, y, \text{revenue}) \}$
  - $\text{phase} \in \{ \text{operating} \}$
  - $\sigma \in [0, 7]$ (time remaining until end of week)
  - $x, y \in \mathbb{R}$ (spatial coordinates)
  - $\text{revenue} \in \mathbb{R}_{0}^{+}$
- **Time Advance Function ($ta$):**
  - $ta(s) = \sigma$
- **External Transition Function ($\delta_{ext}$):**
  - Upon receiving $v$ (cost) at elapsed time $e$:
  - $\text{revenue} = \text{revenue} + v$
  - $\sigma = \sigma - e$ (Continue counting down to the end of the week)
- **Internal Transition Function ($\delta_{int}$):**
  - Triggered at the end of the week ($\sigma = 0$).
  - Calculate Profit: $\pi = \text{revenue} - \text{RunningCost} - \text{Tax}$
  - State update: $\text{revenue} = 0$, $\sigma = 7$
- **Output Function ($\lambda$):**
  - Evaluated just before $\delta_{int}$ when $\sigma=0$.
  - Let $\pi$ be the calculated profit.
  - If $\pi > \text{ProfitThreshold}$: With probability $P_{open}$, emit $\text{open}(x', y')$ where $(x', y')$ is the cell maximizing $\frac{\text{PeopleDensity}}{\text{RestaurantDensity}}$.
  - If $\pi < \text{ProfitThreshold}$: With probability $P_{close}$, emit $\text{close}$.
  - Otherwise: Emit nothing ($\emptyset$).
- **Confluent Transition Function ($\delta_{con}$):**
  - If a person arrives exactly at the end of the week, process $\delta_{ext}$ (add revenue) first, then process $\delta_{int}$ (calculate profit with the new revenue).

---

## Conclusion

By mapping the C16 definition into Zeigler's Formal DEVS formalism, the discrete time leaps (1 to 8 days for people, exactly 7 days for financial accounting) become strictly bounded $\sigma$ values, while the spatial density calculation maps to a structural DSDEVS dynamic topology operation handled by the executive coordinator reacting to $\text{open}(x',y')$ and $\text{close}$ outputs.

---

## 4. Variant 2: General NSA-DEVS Execution Semantics

To accommodate the rigorous verification of discrete-event ordering without the ambiguity of floating-point simultaneity, the system can be reformulated using **Non-Standard Analysis DEVS (NSA-DEVS)**. This approach replaces the classical time base $\mathbb{R}_{0}^{+}$ with a restricted hyperreal time basis $\mathbb{T} = \mathbb{Q} \times \mathbb{N}$, representing superdense time $t = a + b\epsilon$.

This variant is specifically designed to run on the exact rational macro time plus integer microsteps scheduler implemented in this repository (`HyperTime`).

### 4.1. NSA-DEVS Theoretical Modeling

In NSA-DEVS, the state and transition functions explicitly account for infinitesimal delays ($\epsilon$).

**Person Atomic Model ($M_p^{nsa}$):**
- **State ($S$):** $(\text{phase}, (t_{macro}, t_{micro}), x, y)$
- **Time Advance ($ta$):** Returns a hyperreal value. When scheduling a dining event in $d$ days: $ta(s) = (d, 0)$.
- **Output ($\lambda$):** Emits $\text{visit}(cost)$ at the hyperreal time $(t, 0)$.
- **Internal Transition ($\delta_{int}$):** Calculates the next dining interval $d$ and advances state.

**Restaurant Atomic Model ($M_r^{nsa}$):**
- **State ($S$):** $(\text{phase}, (t_{macro}, t_{micro}), \text{revenue})$
- **Time Advance ($ta$):** The time until the end of the 7-day accounting cycle. If scheduled at $(7k, 0)$, $ta(s) = (7, 0) - (e_{macro}, e_{micro})$.
- **External Transition ($\delta_{ext}$):**
  - Upon receiving $\text{visit}$ at elapsed hyperreal time $e$:
  - $\text{revenue} += cost$
  - The restaurant's remaining time until accounting must account for the elapsed time exactly in the hyperreal domain.
- **Internal Transition ($\delta_{int}$):**
  - Evaluates profit and determines structural changes.
  - To prevent causal loops where a restaurant opens/closes and affects an event occurring at the exact same macro-time, the structural output (`open`/`close`) is emitted with an infinitesimal delay: $ta(s) = (0, 1)$ or $ta(s) = \epsilon$.

### 4.2. NSA-DEVS Execution Algorithm

The execution algorithm for the NSA-DEVS variant utilizes a priority queue strictly ordered by the `HyperTime` tuples $(t_{macro}, t_{micro})$.

**Algorithm: NSA-DEVS Executive Coordinator**

1. **Initialization:**
   - For all $d \in D$: Initialize state $s_d$, calculate $ta(s_d) = (t_m, t_{\mu})$.
   - Set $t_{last} = (0, 0)$.
   - Insert all $d$ into Priority Queue $Q$ keyed by $t_{next} = t_{last} + ta(s_d)$.

2. **Main Loop (while $Q$ is not empty and $t_{last} \le t_{end}$):**
   - **Pop:** Extract the component $d^*$ with the minimum hyperreal time $t_{min} = (t_m, t_{\mu})$ from $Q$.
   - **Macro-time Advance:**
     - If $t_m > t_{last.macro}$: $t_{last} \leftarrow (t_m, 0)$.
   - **Micro-time Advance:**
     - If $t_m == t_{last.macro}$ and $t_{\mu} > t_{last.micro}$: $t_{last} \leftarrow (t_m, t_{\mu})$.

   - **Output Phase:**
     - Execute output function: $y_{d^*} = \lambda(s_{d^*})$.

   - **Routing Phase (External Transitions):**
     - For all components $c \in D$ connected to $d^*$ where $y_{d^*}$ acts as an input $x_c$:
       - Calculate elapsed time $e_c = t_{last} - t_{last\_event}(c)$.
       - Execute $\delta_{ext}(s_c, e_c, x_c)$.
       - Update $t_{next}(c) = t_{last} + ta(s_c)$.
       - Adjust $c$ in $Q$.

   - **Internal Transition:**
     - Execute $\delta_{int}(s_{d^*})$.
     - Update $t_{next}(d^*) = t_{last} + ta(s_{d^*})$.
     - Re-insert $d^*$ into $Q$.

   - **Structural Dynamics (DSDEVS Integration):**
     - If $y_{d^*}$ contains `open(x,y)`: Instantiate new component $r_{new}$, initialize, calculate $ta$, and insert into $Q$.
     - If $y_{d^*}$ contains `close`: Remove $d^*$ from $Q$ and from $D$.

By separating macro-time (days/weeks) from micro-time (structural causal chaining like opening a restaurant acting upon subsequent routing logic), the NSA-DEVS algorithm guarantees deterministic structural verification without arbitrary floating-point collision resolutions.

