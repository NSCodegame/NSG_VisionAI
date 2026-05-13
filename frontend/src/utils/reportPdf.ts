/**
 * reportPdf.ts — Client-side PDF generation for NSG VisionAI intelligence reports
 *
 * Generates a classified-looking PDF document from seed report data.
 * No server required — runs entirely in the browser via jsPDF.
 */

import { jsPDF } from "jspdf";
import { SEED_REPORTS } from "../data/seedData";

// Classification header colours (RGB)
const CLASSIFICATION_STYLES: Record<string, { r: number; g: number; b: number; label: string }> = {
  SECRET:       { r: 220, g: 38,  b: 38,  label: "//SECRET//"       },
  TOP_SECRET:   { r: 234, g: 88,  b: 12,  label: "//TOP SECRET//"   },
  CONFIDENTIAL: { r: 37,  g: 99,  b: 235, label: "//CONFIDENTIAL//" },
  RESTRICTED:   { r: 100, g: 116, b: 139, label: "//RESTRICTED//"   },
};

// Full report content keyed by report ID
const REPORT_CONTENT: Record<string, {
  incident_summary: string;
  timeline: { time: string; event: string }[];
  threat_assessment: string;
  recommended_actions: string[];
  officers_assigned: string[];
  evidence_references: string[];
  related_alerts: string[];
}> = {
  "rpt-001-cp-incident": {
    incident_summary:
      "At 08:42 IST on 13 May 2026, NSG VisionAI facial recognition system detected Rashid Ahmed Khan " +
      "(WL-001, KNOWN_TERRORIST) at Connaught Place North Gate with 94% confidence. Two minutes later, " +
      "a weapon-like object was detected in the same frame. Rapid Response Team Alpha was deployed. " +
      "Subject evaded initial cordon. Vehicle DL 3C AK 7741 (White Innova) tracked on CCTV towards Patel Chowk.",
    timeline: [
      { time: "08:31:05", event: "Subject detected at Rajiv Chowk Metro Station (89% confidence)" },
      { time: "08:42:17", event: "P1 CRITICAL — Watchlist match at CP-GATE-A (94% confidence)" },
      { time: "08:44:03", event: "P1 CRITICAL — Weapon-like object detected in same frame (87% confidence)" },
      { time: "08:46:30", event: "Alert acknowledged by NSG/OP/0001. RRT Alpha deployed." },
      { time: "08:52:00", event: "Vehicle DL 3C AK 7741 tracked on CCTV towards Patel Chowk." },
      { time: "09:05:00", event: "Subject lost in Paharganj area. Cordon established." },
    ],
    threat_assessment:
      "THREAT LEVEL: CRITICAL. Subject is a known IED courier with confirmed links to the 2024 Paharganj " +
      "blast. Presence in Connaught Place with a weapon-like object indicates possible imminent threat to " +
      "a high-footfall civilian area. Estimated risk of attack: HIGH.",
    recommended_actions: [
      "Issue immediate detention order for Rashid Ahmed Khan (WL-001)",
      "Increase patrol density at Connaught Place and Rajiv Chowk Metro",
      "Activate CCTV tracking on vehicle DL 3C AK 7741",
      "Alert CISF and Delhi Police SIT for coordinated response",
      "Conduct safe-house sweep in Paharganj area",
    ],
    officers_assigned: ["Cmdr. Vikram Singh (NSG/CMD/0001)", "Opr. Priya Nair (NSG/OP/0001)", "Anl. Rohit Sharma (NSG/ANL/0001)"],
    evidence_references: ["CCTV-CP-GATE-A-20260513-084217.mp4", "FACE-MATCH-WL001-94PCT.jpg", "WEAPON-DETECT-CP-20260513-084403.jpg"],
    related_alerts: ["ALRT-001 (P1 WATCHLIST MATCH)", "ALRT-002 (P1 WEAPON DETECTED)"],
  },
  "rpt-002-rashid-person": {
    incident_summary:
      "Comprehensive intelligence profile on Rashid Ahmed Khan (alias: Raju Bhai / R.A.K.). Subject has " +
      "been sighted 7 times in Delhi NCR over 30 days. Movement pattern analysis suggests safe house in " +
      "Paharganj area. Known associates include 3 individuals under separate surveillance.",
    timeline: [
      { time: "Apr 10", event: "Subject enrolled in NSG VisionAI watchlist (IB/RAW referral)" },
      { time: "Apr 18", event: "First sighting — Noida Sector 18 Market (82% confidence)" },
      { time: "Apr 25", event: "Second sighting — IGI Airport T3 (79% confidence, no boarding)" },
      { time: "May 05", event: "Third sighting — Rajiv Chowk Metro (85% confidence)" },
      { time: "May 11", event: "Vehicle DL 3C AK 7741 spotted near Paharganj" },
      { time: "May 13", event: "P1 CRITICAL alert — CP North Gate (94% confidence)" },
    ],
    threat_assessment:
      "THREAT LEVEL: CRITICAL. Subject has demonstrated operational pattern consistent with pre-attack " +
      "reconnaissance. Repeated visits to high-footfall areas without apparent civilian purpose. " +
      "Recommend immediate detention.",
    recommended_actions: [
      "Issue nationwide lookout notice for Rashid Ahmed Khan",
      "Coordinate with IB and RAW for latest intelligence",
      "Conduct biometric verification at all Delhi NCR checkpoints",
      "Monitor known associates for coordinated movement",
    ],
    officers_assigned: ["Cmdr. Vikram Singh (NSG/CMD/0001)", "Anl. Rohit Sharma (NSG/ANL/0001)"],
    evidence_references: ["WATCHLIST-WL001-PROFILE.pdf", "MOVEMENT-ANALYSIS-30D.xlsx", "ASSOCIATE-NETWORK-MAP.png"],
    related_alerts: ["ALRT-001 (P1 WATCHLIST MATCH)", "ALRT-002 (P1 WEAPON DETECTED)"],
  },
  "rpt-003-igi-zone": {
    incident_summary:
      "Salma Noor Qureshi (WL-003) detected entering restricted airside zone at IGI T3 at 06:10 IST " +
      "without valid airside pass. CISF alerted. Subject was intercepted at Gate 47 and escorted to " +
      "secondary screening. Carry-on baggage flagged for trace explosive residue. Investigation ongoing.",
    timeline: [
      { time: "06:10:22", event: "Salma Qureshi detected at IGI T3 restricted zone (81% confidence)" },
      { time: "06:12:44", event: "P2 HIGH — Zone breach alert triggered (2nd occurrence)" },
      { time: "06:15:00", event: "CISF Gate 47 alerted. Subject intercepted." },
      { time: "06:22:00", event: "Secondary screening initiated. Baggage flagged for trace residue." },
      { time: "07:00:00", event: "Zone activity report generated." },
    ],
    threat_assessment:
      "THREAT LEVEL: HIGH. Subject has been flagged at IGI T3 customs twice in 90 days. Trace explosive " +
      "residue on baggage is a significant indicator. Diplomatic-adjacent travel documents require " +
      "verification with MEA.",
    recommended_actions: [
      "Detain Salma Qureshi for full forensic examination",
      "Verify travel documents with Ministry of External Affairs",
      "Review all IGI T3 footage for the past 90 days",
      "Coordinate with CISF for enhanced screening protocols",
    ],
    officers_assigned: ["Cmdr. Vikram Singh (NSG/CMD/0001)", "CISF Inspector Ramesh Kumar"],
    evidence_references: ["IGI-T3-DEP-07-20260513-061022.mp4", "BAGGAGE-RESIDUE-REPORT.pdf"],
    related_alerts: ["ALRT-003 (P2 ZONE BREACH)"],
  },
  "rpt-004-metro-timeline": {
    incident_summary:
      "Timeline reconstruction of Farhan Iqbal Siddiqui (WL-005) at Rajiv Chowk Metro Station. Subject " +
      "entered at 07:42, loitered near Gate 2 for 16 minutes, connected to public Wi-Fi 3 times. " +
      "Suspected SIM-swap operation targeting commuters. Cyber Wing notified.",
    timeline: [
      { time: "07:42:00", event: "Farhan Siddiqui enters Rajiv Chowk Metro via Gate 2" },
      { time: "07:44:15", event: "Subject connects to public Wi-Fi (DMRC_FREE_WIFI)" },
      { time: "07:51:30", event: "Second Wi-Fi connection. Suspected packet injection." },
      { time: "07:55:10", event: "P3 MEDIUM — Loitering alert triggered (3rd occurrence)" },
      { time: "07:58:22", event: "Third Wi-Fi connection. CBI Cyber Wing notified." },
      { time: "08:01:00", event: "Subject departs towards Blue Line platform." },
    ],
    threat_assessment:
      "THREAT LEVEL: MEDIUM. Subject's behaviour is consistent with SIM-swap attack methodology. " +
      "Three Wi-Fi connections in 16 minutes at a high-footfall location suggests active exploitation " +
      "of commuter devices. Financial institutions should be alerted.",
    recommended_actions: [
      "Alert HDFC and SBI fraud teams for unusual SIM-swap activity",
      "Request DMRC Wi-Fi logs for 07:42–08:01 window",
      "Issue surveillance order for Farhan Siddiqui",
      "Coordinate with CBI Cyber Wing for digital forensics",
    ],
    officers_assigned: ["Anl. Rohit Sharma (NSG/ANL/0001)", "CBI Cyber Wing Inspector Deepa Menon"],
    evidence_references: ["METRO-RCH-02-20260513-075510.mp4", "WIFI-LOG-DMRC-20260513.csv"],
    related_alerts: ["ALRT-004 (P3 LOITERING)"],
  },
  "rpt-005-weekly-ops": {
    incident_summary:
      "Week of 06–13 May 2026. Total alerts: 47. P1 Critical: 3. Watchlist matches: 5. Zone breaches: 8. " +
      "Persons tracked: 23. AI detection accuracy: 91.4%. Camera uptime: 98.2%. Notable incidents: " +
      "Rashid Khan sighting (CP), Salma Qureshi IGI breach, Devraj Menon Gurugram surveillance.",
    timeline: [
      { time: "May 07", event: "2 P2 HIGH alerts — Noida Sector 18 vehicle surveillance" },
      { time: "May 09", event: "1 P1 CRITICAL — Arjun Tiwari vehicle spotted near Ghaziabad border" },
      { time: "May 11", event: "Arjun Tiwari vehicle UP 16 AT 8812 tracked in Noida" },
      { time: "May 12", event: "Devraj Menon identified at Cyber City Gurugram (88% confidence)" },
      { time: "May 13", event: "Rashid Khan P1 CRITICAL at Connaught Place. Salma Qureshi IGI breach." },
    ],
    threat_assessment:
      "THREAT LEVEL: HIGH (elevated from AMBER). Multiple high-value targets active in Delhi NCR " +
      "simultaneously. Pattern suggests coordinated operational activity. Recommend THREATCON BRAVO " +
      "for all NSG-monitored zones.",
    recommended_actions: [
      "Elevate threat level to THREATCON BRAVO across Delhi NCR",
      "Increase camera AI processing frequency to 10fps",
      "Deploy additional RRT units at Connaught Place and IGI",
      "Coordinate weekly briefing with IB, RAW, and Delhi Police",
      "Review and update watchlist with latest intelligence",
    ],
    officers_assigned: ["Cmdr. Vikram Singh (NSG/CMD/0001)", "Anl. Rohit Sharma (NSG/ANL/0001)", "Opr. Priya Nair (NSG/OP/0001)"],
    evidence_references: ["WEEKLY-ANALYTICS-06-13-MAY-2026.xlsx", "CAMERA-UPTIME-REPORT.pdf", "AI-ACCURACY-METRICS.json"],
    related_alerts: ["ALRT-001", "ALRT-002", "ALRT-003", "ALRT-004", "ALRT-005"],
  },
};

export function generateReportPdf(reportId: string): void {
  const report = SEED_REPORTS.find((r) => r.id === reportId);
  if (!report) {
    alert("Report data not found.");
    return;
  }

  const content = REPORT_CONTENT[reportId];
  const classStyle = CLASSIFICATION_STYLES[report.classification] ?? CLASSIFICATION_STYLES.RESTRICTED;

  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const margin = 20;
  const contentW = pageW - margin * 2;
  let y = 0;

  // ── Helper functions ──────────────────────────────────────────────────

  const addPage = () => {
    doc.addPage();
    y = 0;
    drawClassificationBanner();
    y = 18;
  };

  const checkPageBreak = (needed: number) => {
    if (y + needed > pageH - 18) addPage();
  };

  const drawClassificationBanner = () => {
    // Top banner
    doc.setFillColor(classStyle.r, classStyle.g, classStyle.b);
    doc.rect(0, 0, pageW, 10, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.text(classStyle.label, pageW / 2, 6.5, { align: "center" });

    // Bottom banner
    doc.setFillColor(classStyle.r, classStyle.g, classStyle.b);
    doc.rect(0, pageH - 10, pageW, 10, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(7);
    doc.text(
      `${classStyle.label}  |  NSG VisionAI Intelligence Platform  |  ALPHA-01`,
      pageW / 2,
      pageH - 4,
      { align: "center" }
    );
  };

  const sectionHeader = (title: string) => {
    checkPageBreak(12);
    doc.setFillColor(15, 23, 42);
    doc.rect(margin, y, contentW, 8, "F");
    doc.setTextColor(0, 242, 255);
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.text(title.toUpperCase(), margin + 3, y + 5.5);
    y += 11;
  };

  const bodyText = (text: string, indent = 0) => {
    doc.setTextColor(60, 60, 80);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    const lines = doc.splitTextToSize(text, contentW - indent);
    checkPageBreak(lines.length * 5 + 2);
    doc.text(lines, margin + indent, y);
    y += lines.length * 5 + 2;
  };

  const labelValue = (label: string, value: string) => {
    checkPageBreak(7);
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(100, 116, 139);
    doc.text(label.toUpperCase() + ":", margin, y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(30, 30, 50);
    const lines = doc.splitTextToSize(value, contentW - 45);
    doc.text(lines, margin + 45, y);
    y += lines.length * 5 + 1;
  };

  const bulletItem = (text: string, bullet = "•") => {
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(60, 60, 80);
    const lines = doc.splitTextToSize(text, contentW - 8);
    checkPageBreak(lines.length * 5 + 1);
    doc.text(bullet, margin + 2, y);
    doc.text(lines, margin + 7, y);
    y += lines.length * 5 + 1;
  };

  // ── Page 1 ────────────────────────────────────────────────────────────

  drawClassificationBanner();
  y = 18;

  // NSG Logo / Header
  doc.setFillColor(5, 7, 10);
  doc.rect(margin, y, contentW, 22, "F");
  doc.setTextColor(0, 242, 255);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text("NSG VisionAI", margin + 4, y + 9);
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139);
  doc.text("TACTICAL VIDEO INTELLIGENCE PLATFORM", margin + 4, y + 15);
  doc.setFontSize(8);
  doc.setTextColor(classStyle.r, classStyle.g, classStyle.b);
  doc.text(classStyle.label, pageW - margin - 4, y + 9, { align: "right" });
  doc.setTextColor(100, 116, 139);
  doc.text("SECURE NODE: ALPHA-01", pageW - margin - 4, y + 15, { align: "right" });
  y += 26;

  // Report title
  doc.setTextColor(10, 10, 20);
  doc.setFontSize(13);
  doc.setFont("helvetica", "bold");
  const titleLines = doc.splitTextToSize(report.title, contentW);
  doc.text(titleLines, margin, y);
  y += titleLines.length * 7 + 3;

  // Report type badge
  doc.setFillColor(classStyle.r, classStyle.g, classStyle.b);
  doc.roundedRect(margin, y, 50, 6, 1, 1, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(7);
  doc.setFont("helvetica", "bold");
  doc.text(report.report_type.replace(/_/g, " "), margin + 3, y + 4.2);
  y += 10;

  // Metadata block
  doc.setDrawColor(200, 210, 220);
  doc.setLineWidth(0.3);
  doc.rect(margin, y, contentW, 28);
  const meta = [
    ["REPORT ID",   report.id.toUpperCase()],
    ["GENERATED",   new Date(report.generated_at ?? "").toLocaleString("en-IN")],
    ["STATUS",      report.status],
    ["CLASSIFICATION", report.classification],
  ];
  const colW = contentW / 2;
  meta.forEach(([label, value], i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const mx = margin + col * colW + 4;
    const my = y + row * 12 + 7;
    doc.setFontSize(7);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(100, 116, 139);
    doc.text(label + ":", mx, my);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(20, 20, 40);
    doc.text(value, mx, my + 4.5);
  });
  y += 32;

  if (!content) {
    // Fallback if no detailed content
    sectionHeader("Executive Summary");
    bodyText(report.summary ?? "No summary available.");
    doc.save(`${report.id}.pdf`);
    return;
  }

  // ── Incident Summary ──────────────────────────────────────────────────
  sectionHeader("Incident Summary");
  bodyText(content.incident_summary);
  y += 3;

  // ── Timeline ──────────────────────────────────────────────────────────
  sectionHeader("Incident Timeline");
  content.timeline.forEach(({ time, event }) => {
    checkPageBreak(7);
    doc.setFontSize(8);
    doc.setFont("courier", "bold");
    doc.setTextColor(0, 180, 200);
    doc.text(time, margin + 2, y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(50, 50, 70);
    const lines = doc.splitTextToSize(event, contentW - 28);
    doc.text(lines, margin + 26, y);
    y += lines.length * 5 + 1;
  });
  y += 3;

  // ── Threat Assessment ─────────────────────────────────────────────────
  sectionHeader("Threat Assessment");
  bodyText(content.threat_assessment);
  y += 3;

  // ── Recommended Actions ───────────────────────────────────────────────
  sectionHeader("Recommended Actions");
  content.recommended_actions.forEach((action, i) => {
    bulletItem(action, `${i + 1}.`);
  });
  y += 3;

  // ── Officers Assigned ─────────────────────────────────────────────────
  checkPageBreak(30);
  sectionHeader("Officers Assigned");
  content.officers_assigned.forEach((officer) => bulletItem(officer));
  y += 3;

  // ── Evidence References ───────────────────────────────────────────────
  sectionHeader("Evidence References");
  content.evidence_references.forEach((ref) => bulletItem(ref, "→"));
  y += 3;

  // ── Related Alerts ────────────────────────────────────────────────────
  sectionHeader("Related Alerts");
  content.related_alerts.forEach((alert) => bulletItem(alert, "⚠"));
  y += 6;

  // ── Signature block ───────────────────────────────────────────────────
  checkPageBreak(30);
  doc.setDrawColor(200, 210, 220);
  doc.setLineWidth(0.3);
  doc.line(margin, y, margin + 60, y);
  doc.line(pageW - margin - 60, y, pageW - margin, y);
  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text("Authorised Signatory", margin, y + 4);
  doc.text("Reviewing Officer", pageW - margin - 60, y + 4);
  doc.text("NSG VisionAI — ALPHA-01", pageW / 2, y + 4, { align: "center" });

  // ── Save ──────────────────────────────────────────────────────────────
  const filename = `NSG-${report.id.toUpperCase()}-${report.classification}.pdf`;
  doc.save(filename);
}
