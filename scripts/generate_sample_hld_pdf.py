"""
Script to generate realistic AUTOSAR High-Level Design (HLD) sample PDFs using reportlab.
Generates:
1. data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf
2. data/sample/AUTOSAR_BodyControl_HLD_v2.0.pdf (with modified interfaces and added components for version comparison)
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

def create_hld_pdf(filename: str, version: str = "v1.0"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    story = []

    # Title Page
    story.append(Paragraph(f"AUTOSAR High-Level Design Specification ({version})", title_style))
    story.append(Paragraph("System Architecture: Body Control & Exterior Lighting Subsystem", h2_style))
    story.append(Paragraph(f"Document Revision: {version} | Standard: AUTOSAR Classic Platform Release 4.4.0", body_style))
    story.append(Paragraph("Confidentiality: Internal Engineering Reference | ISO 26262 ASIL-B Certified Item", body_style))
    story.append(Spacer(1, 20))

    # Section 1: Executive Scope & Objectives
    story.append(Paragraph("1. System Architectural Overview", h2_style))
    story.append(Paragraph(
        "This High-Level Design document specifies the software architecture for the Body Control Module (BCM). "
        "The BCM coordinates vehicle access, central door locking, exterior lighting control, and low-power standby modes. "
        "All software components adhere to the AUTOSAR component model communicating via the Virtual Function Bus (VFB) and "
        "Runtime Environment (RTE).",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Section 2: Software Components (SWC) Inventory
    story.append(Paragraph("2. Software Components (SWC) Definition", h2_style))
    story.append(Paragraph(
        "The subsystem decomposes into the following architectural Software Components:",
        body_style
    ))

    if version == "v1.0":
        swc_data = [
            ["Component Name", "SWC Type", "Execution Period", "Safety Category"],
            ["BodyControlSWC", "Application SWC", "10 ms (Cyclic)", "QM"],
            ["DoorControlSWC", "Sensor-Actuator SWC", "20 ms (Cyclic)", "ASIL-B"],
            ["LightingSWC", "Application SWC", "50 ms (Cyclic)", "ASIL-A"],
            ["PowerDistributionSWC", "Service SWC", "100 ms (Event-driven)", "ASIL-B"],
        ]
    else:
        # v2.0 introduces TelematicsGatewaySWC and upgrades LightingSWC
        swc_data = [
            ["Component Name", "SWC Type", "Execution Period", "Safety Category"],
            ["BodyControlSWC", "Application SWC", "10 ms (Cyclic)", "QM"],
            ["DoorControlSWC", "Sensor-Actuator SWC", "20 ms (Cyclic)", "ASIL-B"],
            ["LightingSWC", "Application SWC", "20 ms (Cyclic - Modified)", "ASIL-B"],
            ["PowerDistributionSWC", "Service SWC", "100 ms (Event-driven)", "ASIL-B"],
            ["TelematicsGatewaySWC", "Application SWC (New)", "50 ms (Event-driven)", "ASIL-B"],
        ]

    t = Table(swc_data, colWidths=[150, 130, 110, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # Page Break for multi-page structure
    story.append(PageBreak())

    # Section 3: Interface & Port Specifications
    story.append(Paragraph("3. Interface and Port Configuration", h2_style))
    story.append(Paragraph(
        "Software components interact strictly via AUTOSAR ports and interfaces configured in the AUTOSAR XML (ARXML) schema.",
        body_style
    ))

    if version == "v1.0":
        if_data = [
            ["Interface Name", "Interface Type", "Data Elements / Operations", "Cycle Time"],
            ["DoorStatus_If", "Sender-Receiver", "DoorState (uint8), LockStatus (boolean)", "20 ms"],
            ["LightControl_If", "Client-Server", "SetHeadlightState(uint8), GetFault()", "Aperiodic"],
            ["PowerMode_If", "Mode-Switch", "VehiclePowerState {OFF, ACC, RUN}", "Event"],
        ]
    else:
        # v2.0 introduces RemoteCommand_If and modifies DoorStatus_If
        if_data = [
            ["Interface Name", "Interface Type", "Data Elements / Operations", "Cycle Time"],
            ["DoorStatus_If", "Sender-Receiver", "DoorState (uint8), LockStatus (boolean), LatchSpeed (float32)", "20 ms"],
            ["LightControl_If", "Client-Server", "SetHeadlightState(uint8), GetFault()", "Aperiodic"],
            ["PowerMode_If", "Mode-Switch", "VehiclePowerState {OFF, ACC, RUN}", "Event"],
            ["RemoteCommand_If", "Sender-Receiver (New)", "RemoteLockReq (uint8), RemoteHazards (uint8)", "10 ms"],
        ]

    t2 = Table(if_data, colWidths=[130, 100, 180, 90])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    story.append(t2)
    story.append(Spacer(1, 15))

    # Section 4: Port Connections & Inter-Component Dependencies
    story.append(Paragraph("4. Port Connections and Dependencies", h2_style))
    story.append(Paragraph(
        "The following assembly connectors bind the required and provided ports across component boundaries:",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Conn_DoorStatus</b>: Provided Port <i>DoorControlSWC.P_DoorStatus</i> connects to Required Port <i>BodyControlSWC.R_DoorStatus</i> using interface <b>DoorStatus_If</b>.",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Conn_LightControl</b>: Provided Port <i>BodyControlSWC.P_LightControl</i> connects to Required Port <i>LightingSWC.R_LightControl</i> using interface <b>LightControl_If</b>.",
        body_style
    ))
    story.append(Paragraph(
        "• <b>Conn_PowerMode</b>: Provided Port <i>PowerDistributionSWC.P_PowerMode</i> broadcasts power mode changes to <i>BodyControlSWC.R_PowerMode</i>.",
        body_style
    ))

    if version == "v2.0":
        story.append(Paragraph(
            "• <b>Conn_Telematics</b>: Provided Port <i>TelematicsGatewaySWC.P_RemoteCommand</i> connects to <i>BodyControlSWC.R_RemoteCommand</i> using interface <b>RemoteCommand_If</b>.",
            body_style
        ))

    story.append(Spacer(1, 15))

    # Page Break for Section 5
    story.append(PageBreak())

    # Section 5: Functional Flows & Timing
    story.append(Paragraph("5. Functional Execution Flow & Timing Constraints", h2_style))
    story.append(Paragraph(
        "<b>Scenario 1: Driver Door Unlock Sequence</b><br/>"
        "1. The physical driver door handle capacitive sensor triggers an interrupt in the BSW I/O Hardware Abstraction.<br/>"
        "2. The <i>DoorControlSWC</i> runnable <i>Run_ReadDoorSensors</i> executes and validates debounce timer (50 ms).<br/>"
        "3. <i>DoorControlSWC</i> transmits <i>DoorStatus_If.DoorState = UNLOCKED</i> via sender-receiver port <i>P_DoorStatus</i>.<br/>"
        "4. RTE delivers the signal to <i>BodyControlSWC</i>, activating runnable <i>Run_ProcessDoorEvents</i>.<br/>"
        "5. <i>BodyControlSWC</i> commands <i>LightingSWC</i> via client-server call <i>SetHeadlightState(WELCOME_LIGHT)</i>.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Section 6: Inconsistency / Safety Observations
    story.append(Paragraph("6. Architectural Constraints & Diagnostics", h2_style))
    story.append(Paragraph(
        "Under ISO 26262 requirements, all inter-SWC communications crossing QM to ASIL boundaries must enforce "
        "memory partitioning and End-to-End (E2E) protection profiles. "
        "Specifically, <i>DoorControlSWC</i> (ASIL-B) transmission to <i>BodyControlSWC</i> (QM) must implement E2E Profile 01.",
        body_style
    ))

    doc.build(story)
    print(f"Generated {filename} (Version {version}) successfully.")

if __name__ == "__main__":
    create_hld_pdf("data/sample/AUTOSAR_BodyControl_HLD_v1.0.pdf", version="v1.0")
    create_hld_pdf("data/sample/AUTOSAR_BodyControl_HLD_v2.0.pdf", version="v2.0")
