# AUTOSAR HLD AI Assistant — Evaluation Benchmark

This report documents the quantitative and qualitative evaluation of the RAG question-answering pipeline using authentic AUTOSAR High-Level Design (HLD) documents: `AUTOSAR_BodyControl_HLD_v1.0.pdf` and `AUTOSAR_BodyControl_HLD_v2.0.pdf`.

---

## 1. Evaluation Methodology

A 10-item deterministic evaluation benchmark was designed to test the assistant across key automotive engineering dimensions:
1. **Subsystem Architecture & Scope**
2. **Component Interface Definitions**
3. **Port Connections & Connectors**
4. **Runnable Timing & Debounce Constraints**
5. **Functional Execution Flow Sequences**
6. **Safety & ISO 26262 E2E Requirements**
7. **Cross-Version Evolutionary Differences (v1.0 vs v2.0)**
8. **Table-Derived Metrics & Port Specifications**
9. **Negative Control: Unsupported Hardware Specifications**
10. **Negative Control: Unsupported Network Bus Rates**

### Evaluation Criteria
- **Answer Correctness**: Factual agreement with the source AUTOSAR HLD document.
- **Traceable Page Citations**: Citations must point to the exact document page where the architectural fact originates.
- **Groundedness**: The assistant must not hallucinate facts absent from the retrieved evidence.
- **Controlled Refusal**: For unsupported inquiries, the assistant must return:
  `"Insufficient evidence in the selected HLD documents to answer this question."`

---

## 2. Evaluation Results Summary

| Metric | Target | Actual Result |
|---|---|---|
| **Total Evaluation Questions** | 10 | 10 |
| **Overall Benchmark Pass Rate** | $\ge 90\%$ | **100.0% (10/10)** |
| **Supported Question Factual Accuracy** | $\ge 90\%$ | **100.0% (8/8)** |
| **Citation Page Correctness** | $100\%$ | **100.0% (8/8)** |
| **Negative Control Refusal Rate** | $100\%$ | **100.0% (2/2)** |
| **False Positive Hallucination Count** | 0 | **0** |

---

## 3. Item-by-Item Benchmark Verification Log

### [EVAL-01] Subsystem Scope & Components
- **Question**: *"What is the architectural scope of the Body Control Module subsystem?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 1
- **Retrieved Chunks**: 4 chunks (Page 1)
- **Confidence**: `0.7253 (HIGH)`
- **Answer Summary**: Accurately describes BCM coordinating vehicle access, central door locking, exterior lighting control, and low-power standby modes adhering to AUTOSAR component model.
- **Citations**: Page 1, Section: `1. System Architectural Overview`
- **Result**: **PASS**

### [EVAL-02] Component Interfaces
- **Question**: *"Which software components communicate via LightControl_If?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 2
- **Retrieved Chunks**: 4 chunks (Page 2, Page 3)
- **Confidence**: `0.5264 (MEDIUM)`
- **Answer Summary**: Correctly identifies `BodyControlSWC` and `LightingSWC` communicating via `LightControl_If`.
- **Citations**: Page 2, Section: `4. Port Connections and Dependencies`
- **Result**: **PASS**

### [EVAL-03] Ports & Connectors
- **Question**: *"Which ports connect DoorControlSWC and BodyControlSWC?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 2
- **Retrieved Chunks**: 4 chunks (Page 2)
- **Confidence**: `0.6634 (HIGH)`
- **Answer Summary**: Correctly identifies Provided Port `DoorControlSWC.P_DoorStatus` connecting to Required Port `BodyControlSWC.R_DoorStatus` using interface `DoorStatus_If`.
- **Citations**: Page 2, Section: `4. Port Connections and Dependencies`
- **Result**: **PASS**

### [EVAL-04] Runnable Timing
- **Question**: *"What is the cycle time and debounce timer of Run_ReadDoorSensors?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 3
- **Retrieved Chunks**: 4 chunks (Page 3)
- **Confidence**: `0.5419 (MEDIUM)`
- **Answer Summary**: Accurately reports cyclic execution period of 20 ms with a 50 ms debounce timer.
- **Citations**: Page 3, Section: `Scenario 1: Driver Door Unlock Sequence`
- **Result**: **PASS**

### [EVAL-05] Functional Execution Flow
- **Question**: *"What triggers Scenario 1: Driver Door Unlock Sequence?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 3
- **Retrieved Chunks**: 4 chunks (Page 3)
- **Confidence**: `0.8465 (HIGH)`
- **Answer Summary**: Correctly identifies physical driver door handle capacitive sensor triggering an interrupt in BSW I/O Hardware Abstraction.
- **Citations**: Page 3, Section: `Scenario 1: Driver Door Unlock Sequence`
- **Result**: **PASS**

### [EVAL-06] Safety & ISO 26262
- **Question**: *"What does section 6 specify regarding ISO 26262 requirements for DoorControlSWC?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 3
- **Retrieved Chunks**: 4 chunks (Page 3)
- **Confidence**: `0.5561 (MEDIUM)`
- **Answer Summary**: Correctly cites ISO 26262 inter-SWC communications crossing QM to ASIL boundaries enforcing memory partitioning and End-to-End (E2E) protection.
- **Citations**: Page 3, Section: `6. Architectural Constraints & Diagnostics`
- **Result**: **PASS**

### [EVAL-07] Multi-Version Evolution
- **Question**: *"What changed between the available v1.0 and v2.0 information regarding the body control architecture?"*
- **Target Source**: Cross-version (`v1.0` and `v2.0`), Pages 1-3
- **Retrieved Chunks**: 4 chunks spanning `v1.0` and `v2.0`
- **Confidence**: `0.5665 (MEDIUM)`
- **Answer Summary**: Distinguishes baseline v1.0 architecture from v2.0 expansions (addition of `TelematicsGatewaySWC`, `RemoteCommand_If`, and timing refinements).
- **Citations**: Page 1-3 from both `AUTOSAR_BodyControl_HLD_v1.0.pdf` and `v2.0.pdf`
- **Result**: **PASS**

### [EVAL-08] Table-Derived Metrics
- **Question**: *"What is the execution period and safety category of PowerDistributionSWC in the SWC table?"*
- **Target Source**: `AUTOSAR_BodyControl_HLD_v1.0.pdf`, Page 1
- **Retrieved Chunks**: 4 chunks (Page 1)
- **Confidence**: `0.5535 (MEDIUM)`
- **Answer Summary**: Accurately extracts table metrics: 100 ms (Event-driven) execution period, ASIL-B safety category.
- **Citations**: Page 1, Section: `### [Table Data: Page 1]`
- **Result**: **PASS**

### [EVAL-09] Negative Control — Hardware Part Number
- **Question**: *"What is the exact ECU hardware part number and microprocessor clock speed?"*
- **Target Source**: None (Information not present in HLD)
- **Retrieved Chunks**: 0 chunks passing relevance threshold
- **Confidence**: `0.0000 (INSUFFICIENT)`
- **Answer**: `"Insufficient evidence in the selected HLD documents to answer this question."`
- **Citations**: `[]` (0 citations)
- **Result**: **PASS** (Zero hallucination refusal)

### [EVAL-10] Negative Control — Bus Baud Rate
- **Question**: *"What is the CAN bus baud rate for the body powertrain gateway?"*
- **Target Source**: None (Information not present in HLD)
- **Retrieved Chunks**: 4 weak background chunks
- **Confidence**: `0.3740 (LOW)`
- **Answer**: `"Insufficient evidence in the selected HLD documents to answer this question."`
- **Citations**: Filtered
- **Result**: **PASS** (Zero hallucination refusal)

---

## 4. Evaluation Reproduction
The exact automated benchmark can be re-run at any time using:
```bash
backend\venv\Scripts\python.exe scripts/e2e_demo_verify.py
```
or via pytest:
```bash
backend\venv\Scripts\pytest.exe backend/tests/test_evaluation.py -v
```
