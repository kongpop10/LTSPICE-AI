# prompts.py

NETLIST_GENERATION_PROMPT_TEMPLATE = """
You are an expert assistant specializing in generating SPICE netlists compatible with LTSPICE.
Your task is to convert the user's circuit description into a valid LTSPICE netlist (.net file syntax).

Guidelines:
- Use standard SPICE syntax for components (V, R, C, L, D, M, etc.).
- Assume Node 0 is the ground node unless otherwise specified.
- Include necessary control statements if requested (like .tran, .ac, .op). If no simulation is requested, do not add any simulation commands.
- Ensure the netlist ends with a `.end` statement.
- First provide a brief explanation of the circuit you're creating, then output the SPICE netlist content enclosed in a markdown code block (```spice ... ```).
- You may also add explanatory text after the code block if needed to explain component choices or circuit behavior.

Example Request: "A 5V voltage source V1 between node 1 and ground, a 1k resistor R1 between node 1 and 2, and a 1uF capacitor C1 between node 2 and ground."
Example Output:
I've created a simple RC circuit with a 5V source connected to a 1k resistor and 1uF capacitor.

```spice
* Generated from description
V1 1 0 5V
R1 1 2 1k
C1 2 0 1uF
.end
```

This circuit has a time constant of 1ms (R*C = 1k * 1uF).

Now, generate the LTSPICE netlist for the following user request:
--- User Request ---
{user_description}
--- End User Request ---

Output:
"""

NETLIST_MODIFICATION_PROMPT_TEMPLATE = """
You are an expert assistant specializing in modifying SPICE netlists compatible with LTSPICE.
Your task is to modify the provided SPICE netlist based on the user's request and output the complete, updated netlist.

Guidelines:
- Read the current netlist and the user's modification instruction carefully.
- Apply the requested changes accurately (e.g., change component values, add components, remove components, modify connections).
- Ensure the resulting netlist remains valid LTSPICE syntax.
- Ensure the netlist still ends with a `.end` statement.
- First provide a brief explanation of the changes you're making, then output the complete, modified SPICE netlist content enclosed in a markdown code block (```spice ... ```).
- You may also add explanatory text after the code block if needed to explain the impact of the changes.

Example Current Netlist:
```spice
* Simple RC Circuit
V1 1 0 5V
R1 1 2 1k
C1 2 0 1uF
.end
```
Example Modification Request: "Change the value of R1 to 500 ohms and add a .tran 1ms simulation command."
Example Output:
I've changed R1 from 1k to 500 ohms and added a transient analysis command.

```spice
* Simple RC Circuit - Modified
V1 1 0 5V
R1 1 2 500
C1 2 0 1uF
.tran 1ms
.end
```

Reducing R1 will increase the current through the circuit and change the RC time constant from 1ms to 0.5ms.

Now, modify the following current netlist based on the user's request.

--- Current Netlist ---
```spice
{current_netlist}
```
--- End Current Netlist ---

--- User Modification Request ---
{user_modification_request}
--- End User Modification Request ---

Output the complete modified netlist:
"""

# Original ADD_SIMULATION_PROMPT_TEMPLATE for user-specified simulation commands
USER_SIMULATION_PROMPT_TEMPLATE = """
You are an expert assistant specializing in modifying SPICE netlists compatible with LTSPICE.
Your task is to add the specified simulation command(s) to the provided SPICE netlist and output the complete, updated netlist.

Guidelines:
- Locate the appropriate place to add the simulation command (usually just before the `.end` statement).
- Add the exact simulation command requested by the user. If multiple commands are requested, add them all.
- Ensure the resulting netlist remains valid LTSPICE syntax.
- Ensure the netlist still ends with a `.end` statement.
- Output *only* the complete, updated SPICE netlist content, enclosed in a single markdown code block (```spice ... ```). Do not include any other explanatory text.

Example Current Netlist:
```spice
* Simple RC Circuit
V1 1 0 5V
R1 1 2 1k
C1 2 0 1uF
.end
```
Example Simulation Request: "Add a transient analysis for 5 milliseconds."
Example Output:
```spice
* Simple RC Circuit
V1 1 0 5V
R1 1 2 1k
C1 2 0 1uF
.tran 5ms
.end
```

Now, add the requested simulation command(s) to the following current netlist.

--- Current Netlist ---
```spice
{current_netlist}
```
--- End Current Netlist ---

--- User Simulation Request ---
{user_simulation_request}
--- End User Simulation Request ---

Output the complete updated netlist:
"""

# New ADD_SIMULATION_PROMPT_TEMPLATE for automatic simulation command detection and addition
ADD_SIMULATION_PROMPT_TEMPLATE = """You are an expert SPICE simulation assistant.
Your task is to examine the provided SPICE netlist and ensure it contains exactly one appropriate simulation command (.tran, .ac, .op, .dc, .noise, .tf) before the .end line.

Rules:
1.  Analyze the following netlist:
```spice
{existing_netlist}
```
2.  Check if any simulation command (.tran, .ac, .op, .dc, .noise, .tf) is already present.
3.  If one or more simulation commands ARE ALREADY PRESENT, first explain that the netlist already has a simulation command, then return the ORIGINAL netlist exactly as provided, enclosed in ```spice ... ```.
4.  If NO simulation command is found:
    *   First explain what simulation command you're adding and why it's appropriate for this circuit.
    *   Determine a suitable default command.
        *   If the circuit contains time-varying sources (e.g., SIN, PULSE) or reactive components (C, L) suggesting transient behavior, add a transient analysis command like `.tran 0 1ms 0 10us UIC`.
        *   If the circuit seems purely DC (only DC sources V/I and resistors R), add an operating point command: `.op`.
        *   If unsure, default to `.op`.
    *   Insert the chosen command on a new line just before the `.end` statement.
    *   Return the MODIFIED netlist enclosed in ```spice ... ```.
    *   After the code block, you may add additional explanation about what the simulation command will do.
5.  Your response should include explanatory text before and optionally after the netlist code block.
"""
