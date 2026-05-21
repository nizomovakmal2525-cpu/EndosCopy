import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

public class StatsServer {
    private static final String PYTHON_STATS_BASE_URL = System.getenv().getOrDefault("PYTHON_STATS_BASE_URL", "http://127.0.0.1:8000");
    private static final String INTERNAL_STATS_KEY = System.getenv().getOrDefault("INTERNAL_STATS_KEY", "endoscan-local-stats");
    private static final String CELL_SEP = "\u001f";
    private static final String ROW_SEP = "\u001e";

    private static final String[][] ADMIN_META = {
            {"dashboard", "Welcome to Admin Dashboard", "The global overview of platform activity.", "Search admin data..."},
            {"users", "Users Management", "View registered users and their analysis activity.", "Search users..."},
            {"analyses", "Analysis Records", "Monitor all AI-assisted image analysis results.", "Search analyses..."},
            {"review-queue", "Review Queue", "Cases that may need admin or expert review.", "Search review..."},
            {"dataset", "Dataset Overview", "Manage labeled dataset used by EndoScan AI.", "Search dataset..."},
            {"model-stats", "AI Model Performance", "Monitor model accuracy, confidence, and predictions.", "Search model..."},
            {"reports", "Reports & Export", "Generate platform statistics reports.", "Generate report..."},
            {"news-manager", "News Manager", "Create and manage public news articles.", "Search news..."},
            {"activity-logs", "Activity Logs", "Track admin and user actions in the system.", "Search logs..."},
            {"messages", "User Messages", "Feedback, contact requests, and user reports.", "Search messages..."},
            {"settings", "Settings", "Manage platform configuration.", "Search settings..."},
            {"user-detail", "User Profile: Ali Karim", "Detailed user activity and controls.", "Search user history..."},
            {"analysis-detail", "Analysis Detail #1024", "Detailed AI analysis result and admin notes.", "Search analysis detail..."}
    };

    private static final String[][] USER_META = {
            {"snapshot", "Welcome back", "Your personal AI-assisted analysis overview.", "Search analysis..."},
            {"scan-library", "Scan Library", "All your saved AI-assisted image analyses.", "Search scans..."},
            {"ai-insights", "AI Insights", "Smart summary based on your saved analyses.", "Search insights..."},
            {"risk-map", "Risk Map", "Overview of your analysis risk levels.", "Search risk cases..."},
            {"confidence-pulse", "Confidence Pulse", "Track AI confidence changes across your analyses.", "Search confidence..."},
            {"timeline", "Progress Timeline", "Your analysis journey over time.", "Search timeline..."},
            {"reports", "My Reports", "Download your AI-assisted analysis summaries.", "Search reports..."},
            {"profile", "Profile", "Manage your EndoScan AI account details.", "Search profile..."},
            {"analysis-detail", "Analysis Detail", "Detailed view of one saved AI analysis.", "Search analysis detail..."}
    };

    public static void main(String[] args) throws IOException {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8081"));
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/api/stats", StatsServer::handleStats);
        server.createContext("/health", StatsServer::handleHealth);
        server.setExecutor(null);
        server.start();
        System.out.println("EndoScan Java Stats service started at http://127.0.0.1:" + port);
    }

    private static void handleHealth(HttpExchange exchange) throws IOException {
        send(exchange, 200, "{\"status\":\"ok\",\"service\":\"java-stats\"}");
    }

    private static void handleStats(HttpExchange exchange) throws IOException {
        addCors(exchange);
        if ("OPTIONS".equalsIgnoreCase(exchange.getRequestMethod())) {
            exchange.sendResponseHeaders(204, -1);
            return;
        }

        String[] parts = exchange.getRequestURI().getPath().split("/");
        if (parts.length < 5) {
            send(exchange, 404, "{\"error\":\"Not found\"}");
            return;
        }

        String scope = parts[3].toLowerCase(Locale.ROOT);
        String section = parts[4].toLowerCase(Locale.ROOT);

        if ("admin".equals(scope)) {
            send(exchange, 200, buildPayload(adminPage(section)));
            return;
        }

        if ("user".equals(scope)) {
            send(exchange, 200, buildPayload(userPage(section, queryValue(exchange, "userId"))));
            return;
        }

        send(exchange, 404, "{\"error\":\"Unknown stats scope\"}");
    }

    private static Page adminPage(String section) {
        String[] meta = metaFor(ADMIN_META, section, "dashboard");
        Page p = new Page("admin", meta[0], meta[1], meta[2], meta[3]);
        Snapshot snapshot = Snapshot.load();

        switch (p.section) {
            case "users":
                p.cards = rows(
                        row("Total Users", "2,341", "All accounts"),
                        row("Active Users", "824", "Last 30 days"),
                        row("New Today", "37", "Fresh accounts"),
                        row("Blocked Users", "12", "Restricted"),
                        row("Top Users", "18", "20+ scans"),
                        row("Growth", "+14%", "Monthly")
                );
                p.filters = row("Role", "Status", "Date");
                p.charts = charts(chart("User Growth Chart", "line", row("Apr 1", "1800"), row("Apr 10", "1970"), row("Apr 20", "2130"), row("May 1", "2260"), row("May 17", "2341")));
                p.table = new Table("Users", row("ID", "Name", "Email", "Scans", "Role"), rows(
                        row("1", "Ali Karim", "ali@mail.com", "24", "User"),
                        row("2", "Admin", "admin@endoscan.ai", "120", "Admin"),
                        row("3", "Vali", "vali@mail.com", "8", "User")
                ), row("View", "Block", "Delete", "Make Admin"));
                p.notes = row("Users table is prepared for role, status, and date filtering.", "Opening a user can route to the User Detail page.");
                break;
            case "analyses":
                p.cards = rows(
                        row("Total Scans", "18,920", "All records"),
                        row("Today Scans", "126", "Last 24 hours"),
                        row("Average Confidence", "91.4%", "Mean score"),
                        row("Failed Analyses", "42", "Need retry"),
                        row("Low Confidence", "73", "Below 70%"),
                        row("Most Detected", "Normal", "Top class")
                );
                p.filters = row("Date", "Prediction", "Risk", "Confidence");
                p.charts = charts(chart("Detection Classes", "bars", row("Normal", "58"), row("Polyps", "17"), row("Esophagitis", "14"), row("Ulcerative", "11")));
                p.table = new Table("Analysis Records", row("ID", "User", "Prediction", "Conf.", "Risk"), rows(
                        row("1024", "Ali", "Normal", "94%", "Low"),
                        row("1023", "Vali", "Polyps", "88%", "Medium"),
                        row("1022", "Hasan", "Esophagitis", "86%", "Medium"),
                        row("1021", "Jasur", "Ulcerative", "79%", "High")
                ), row("View Image", "View Details", "Delete"));
                p.detailTarget = "/admin/analysis-detail";
                break;
            case "review-queue":
                p.cards = rows(
                        row("Pending", "18", "Need review"),
                        row("High Risk", "7", "Serious cases"),
                        row("Low Conf.", "11", "Below threshold"),
                        row("Approved", "42", "This month"),
                        row("Marked Review", "9", "Expert queue"),
                        row("Deleted", "2", "Invalid scans")
                );
                p.filters = row("Risk", "Confidence", "Date", "Status");
                p.table = new Table("Cases Needing Review", row("ID", "User", "Prediction", "Conf.", "Status"), rows(
                        row("1", "Ali", "Polyps", "62%", "Pending"),
                        row("2", "Vali", "Ulcerative", "58%", "Pending"),
                        row("3", "Hasan", "Normal", "55%", "Review")
                ), row("View Image", "Approve", "Mark Review", "Delete"));
                p.notes = row("Low-confidence or high-risk analyses are grouped here.", "This keeps risky results visible for admin review.");
                break;
            case "dataset":
                p.cards = rows(
                        row("Total Dataset Images", "8,000+", "Dataset size"),
                        row("Detection Classes", "8+", "Labels"),
                        row("Verified Images", "7,850", "Reviewed"),
                        row("Need Review", "150", "Pending labels"),
                        row("Train", "70%", "Split"),
                        row("Validation/Test", "15% / 15%", "Split")
                );
                p.charts = charts(
                        chart("Dataset by Class", "bars", row("Normal", "38"), row("Polyps", "24"), row("Esophagitis", "20"), row("Ulcerative", "18")),
                        chart("Train / Validation / Test Split", "bars", row("Train", "70"), row("Validation", "15"), row("Test", "15"))
                );
                p.table = new Table("Dataset Table", row("ID", "Image Name", "Class", "Status"), rows(
                        row("1", "img001.jpg", "Normal", "Verified"),
                        row("2", "img002.jpg", "Polyps", "Verified"),
                        row("3", "img003.jpg", "Esophagitis", "Need Review")
                ), row("Add Image", "Import Dataset", "Export CSV"));
                break;
            case "model-stats":
                p.cards = rows(
                        row("Avg Confidence", "91.4%", "Production"),
                        row("Tested Images", "8,000+", "Validation base"),
                        row("Prediction Count", "18,920", "All time"),
                        row("Avg Processing Time", "2.4 sec", "Per scan"),
                        row("Failed Prediction Rate", "0.8%", "Errors"),
                        row("Active Model", "v1.1", "Current")
                );
                p.charts = charts(
                        chart("Confidence Distribution", "bars", row("60-70%", "12"), row("70-80%", "24"), row("80-90%", "41"), row("90-100%", "72")),
                        chart("Class Performance", "bars", row("Normal", "96"), row("Polyps", "91"), row("Esophagitis", "89"), row("Ulcerative", "86"))
                );
                p.table = new Table("Model Versions", row("Version", "Confidence", "Date", "Status"), rows(
                        row("v1.0", "89.1%", "2026-04", "Old"),
                        row("v1.1", "91.4%", "2026-05", "Active")
                ), row("View", "Rollback", "Export"));
                p.panels = panels(
                        panel("Model Health", row("Status", "Online"), row("Last Prediction", "2 minutes ago"), row("Avg Response Time", "2.4 sec"), row("Error Rate", "0.8%"), row("Active Model", "v1.1"))
                );
                break;
            case "reports":
                p.cards = rows(
                        row("Monthly Report", "Ready", "May 2026"),
                        row("User Report", "Ready", "2,341 users"),
                        row("AI Report", "Ready", "18,920 scans"),
                        row("Dataset Report", "Ready", "8,000+ images"),
                        row("CSV Export", "Live", "Data table"),
                        row("PDF Export", "Queued", "Summary")
                );
                p.form = new Form("Generate Report", rows(row("Report Type", "Analyses"), row("Date Range", "2026-05-01 to 2026-05-31"), row("Format", "PDF / Excel / CSV")), row("Total analyses", "Risk distribution", "Prediction classes", "Average confidence"), row("Generate Report", "Download CSV"));
                p.notes = row("Reports cover monthly statistics, users, AI results, and dataset status.", "Export actions are ready for backend report generation later.");
                break;
            case "news-manager":
                p.cards = rows(
                        row("Total News", "18", "All articles"),
                        row("Published News", "14", "Public"),
                        row("Draft News", "4", "In progress"),
                        row("Last Published", "05/12", "Latest"),
                        row("Most Viewed", "AI Update", "Top article"),
                        row("Create News", "+", "New article")
                );
                p.table = new Table("News Articles", row("ID", "Title", "Status", "Date"), rows(
                        row("1", "New AI Model Update", "Public", "05/12"),
                        row("2", "8,000+ Dataset Reached", "Public", "05/08"),
                        row("3", "Medical AI Research Notes", "Draft", "05/01")
                ), row("Edit", "Preview", "Publish", "Delete"));
                break;
            case "activity-logs":
                p.cards = rows(
                        row("Today Logs", "240", "All events"),
                        row("Admin Actions", "38", "Control events"),
                        row("Errors", "6", "Need review"),
                        row("Uploads", "126", "Today"),
                        row("Logins", "84", "Today"),
                        row("System", "Online", "Status")
                );
                p.filters = row("User", "Action", "Date", "Type");
                p.table = new Table("Activity Logs", row("Time", "User", "Action", "Status"), rows(
                        row("10:21", "Admin", "Deleted scan", "Success"),
                        row("10:15", "Ali", "Uploaded image", "Success"),
                        row("10:10", "System", "Model error", "Failed")
                ), row("Open", "Export"));
                break;
            case "messages":
                p.cards = rows(
                        row("Total", "86", "Messages"),
                        row("Unread", "12", "Need response"),
                        row("Replied", "54", "Handled"),
                        row("Pending", "20", "Open"),
                        row("Today", "5", "New"),
                        row("Avg Reply", "2h", "Response")
                );
                p.table = new Table("User Messages", row("ID", "Name", "Subject", "Status"), rows(
                        row("1", "Ali Karim", "Upload issue", "Unread"),
                        row("2", "Vali", "Result help", "Replied"),
                        row("3", "Hasan", "Account", "Pending")
                ), row("Open", "Reply", "Mark Read", "Delete"));
                break;
            case "settings":
                p.panels = panels(
                        panel("General Settings", row("Site Name", "EndoScan AI"), row("Public Stats", "ON"), row("Registration", "ON"), row("Maintenance Mode", "OFF")),
                        panel("AI Settings", row("Active Model", "v1.1"), row("Confidence Threshold", "70%"), row("Save Uploaded Images", "ON")),
                        panel("Security", row("Admin Email", "admin@endoscan.ai"), row("Two Factor Auth", "OFF"), row("Session Timeout", "30 min"))
                );
                p.actions = row("Save Changes");
                break;
            case "user-detail":
                p.cards = rows(
                        row("Total Scans", "24", "User analyses"),
                        row("Avg Confidence", "88%", "Mean score"),
                        row("High Risk", "2", "Serious"),
                        row("Last Login", "Today", "Active")
                );
                p.panels = panels(panel("Profile", row("Email", "ali@mail.com"), row("Role", "User"), row("Status", "Active"), row("Registered", "2026-05-01")));
                p.table = new Table("User Analysis History", row("Date", "Prediction", "Confidence", "Risk"), rows(
                        row("2026-05-17", "Normal", "94%", "Low"),
                        row("2026-05-16", "Polyps", "88%", "Medium")
                ), row("Block User", "Reset Password", "Make Admin", "Delete Account"));
                break;
            case "analysis-detail":
                p.panels = panels(
                        panel("Uploaded Image", row("Preview", "Endoscopy image preview"), row("Image", "uploads/sample.jpg")),
                        panel("AI Result", row("Prediction", "Polyps"), row("Confidence", "88%"), row("Risk Level", "Medium"), row("Processing Time", "2.1 sec"), row("Uploaded By", "Ali Karim"), row("Date", "2026-05-17"))
                );
                p.notes = row("Admin note: This case may require professional review.");
                p.actions = row("Approve", "Mark as Review Needed", "Delete", "Download Result");
                break;
            default:
                p.cards = rows(
                        row("Total Users", "2,341", "Registered accounts"),
                        row("Total Analyses", "18,920", "All analyses"),
                        row("Today Analyses", "126", "Last 24 hours"),
                        row("Average Confidence", "91.4%", "Model confidence"),
                        row("High Risk Cases", "312", "Need review"),
                        row("Dataset Images", "8,000+", "Images")
                );
                p.charts = charts(
                        chart("Analyses Last 7 Days", "line", row("Mon", "42"), row("Tue", "58"), row("Wed", "49"), row("Thu", "76"), row("Fri", "64"), row("Sat", "91"), row("Sun", "126")),
                        chart("Risk Distribution", "bars", row("Low", "58"), row("Medium", "31"), row("High", "11"))
                );
                p.table = new Table("Recent Analyses", row("User", "Prediction", "Confidence", "Risk"), rows(
                        row("Ali", "Normal", "94%", "Low"),
                        row("Vali", "Polyps", "88%", "Medium"),
                        row("Hasan", "Ulcerative", "81%", "High")
                ), row("Open Detail"));
                p.panels = panels(
                        panel("System Alerts", row("Low-confidence analyses", "12 need review"), row("Failed image uploads today", "3"), row("Model response time", "+18%"), row("Dataset status", "Healthy")),
                        panel("Model Health", row("Status", "Online"), row("Last Prediction", "2 minutes ago"), row("Avg Response Time", "2.4 sec"), row("Error Rate", "0.8%"), row("Active Model", "v1.1")),
                        panel("Storage Usage", row("Uploaded Images", "18,920"), row("Storage Used", "4.8 GB"), row("Average Image Size", "260 KB"), row("Old Files Cleanup", "Enabled"))
                );
                p.notifications = row("5 high risk cases detected", "2 failed analyses today", "New user registered", "Dataset import completed");
                break;
        }
        applyAdminSnapshot(p, snapshot);
        return p;
    }

    private static void applyAdminSnapshot(Page p, Snapshot s) {
        if (!s.hasData()) return;

        switch (p.section) {
            case "users":
                p.cards = rows(
                        row("Total Users", s.get("totalUsers", "0"), "All accounts"),
                        row("Active Users", s.get("activeUsers", "0"), "Active accounts"),
                        row("New Today", s.get("newUsersToday", "0"), "Fresh accounts"),
                        row("Blocked Users", s.get("blockedUsers", "0"), "Restricted"),
                        row("Top Users", s.get("topUsers", "0"), "5+ scans"),
                        row("Growth", s.get("userGrowth", "+0%"), "Monthly")
                );
                p.charts = charts(chart("User Growth Chart", "line", s.matrix("chartUserGrowth", row("Today", "0"))));
                p.table = new Table("Users", row("ID", "Name", "Email", "Scans", "Role"), s.matrix("usersRows", row("-", "No users", "-", "0", "-")), row("View", "Block", "Delete", "Make Admin"));
                p.detailTarget = "/admin/user-detail";
                break;
            case "analyses":
                p.cards = rows(
                        row("Total Scans", s.get("totalAnalyses", "0"), "All records"),
                        row("Today Scans", s.get("todayAnalyses", "0"), "Today"),
                        row("Average Confidence", s.get("averageConfidence", "0%"), "Mean score"),
                        row("Failed Analyses", s.get("failedAnalyses", "0"), "Need retry"),
                        row("Low Confidence", s.get("lowConfidenceCases", "0"), "Below threshold"),
                        row("Most Detected", s.get("mostDetectedClass", "No data"), "Top class")
                );
                p.charts = charts(chart("Detection Classes", "bars", s.matrix("chartDetectionClasses", row("No data", "0"))));
                p.table = new Table("Analysis Records", row("ID", "User", "Prediction", "Conf.", "Risk"), s.matrix("analysesRows", row("-", "No data", "-", "-", "-")), row("View Image", "View Details", "Delete"));
                p.detailTarget = "/admin/analysis-detail";
                break;
            case "review-queue":
                p.cards = rows(
                        row("Pending", s.get("reviewPending", "0"), "Need review"),
                        row("High Risk", s.get("reviewHighRisk", "0"), "Serious cases"),
                        row("Low Conf.", s.get("reviewLowConfidence", "0"), "Below threshold"),
                        row("Approved", s.get("reviewApproved", "0"), "Reviewed"),
                        row("Marked Review", s.get("reviewMarked", "0"), "Expert queue"),
                        row("Deleted", s.get("reviewDeleted", "0"), "Invalid scans")
                );
                p.table = new Table("Cases Needing Review", row("ID", "User", "Prediction", "Conf.", "Status"), s.matrix("reviewRows", row("-", "No pending cases", "-", "-", "Clear")), row("View Image", "Approve", "Mark Review", "Delete"));
                p.detailTarget = "/admin/analysis-detail";
                break;
            case "dataset":
                p.cards = rows(
                        row("Total Dataset Images", s.get("datasetImages", "0"), "Dataset size"),
                        row("Detection Classes", s.get("detectionClasses", "0"), "Labels"),
                        row("Verified Images", s.get("verifiedImages", "0"), "Reviewed"),
                        row("Need Review", s.get("needReviewImages", "0"), "Pending labels"),
                        row("Train", "70%", "Split"),
                        row("Validation/Test", "15% / 15%", "Split")
                );
                p.charts = charts(
                        chart("Dataset by Class", "bars", s.matrix("chartDatasetByClass", row("No data", "0"))),
                        chart("Train / Validation / Test Split", "bars", s.matrix("chartTrainSplit", row("Train", "0")))
                );
                p.table = new Table("Dataset Table", row("ID", "Image Name", "Class", "Status"), s.matrix("datasetRows", row("-", "No images", "-", "-")), row("Add Image", "Import Dataset", "Export CSV"));
                break;
            case "model-stats":
                p.cards = rows(
                        row("Avg Confidence", s.get("averageConfidence", "0%"), "Production"),
                        row("Tested Images", s.get("testedImages", "0"), "Validation base"),
                        row("Prediction Count", s.get("predictionCount", "0"), "All time"),
                        row("Avg Processing Time", s.get("avgProcessingTime", "0 sec"), "Per scan"),
                        row("Failed Prediction Rate", s.get("failedPredictionRate", "0%"), "Errors"),
                        row("Active Model", s.get("activeModel", "v1.1"), "Current")
                );
                p.charts = charts(
                        chart("Confidence Distribution", "bars", s.matrix("chartConfidenceDistribution", row("60-70%", "0"))),
                        chart("Class Performance", "bars", s.matrix("chartClassPerformance", row("No data", "0")))
                );
                p.table = new Table("Model Versions", row("Version", "Confidence", "Date", "Status"), s.matrix("modelVersionsRows", row("v1.1", s.get("averageConfidence", "0%"), "2026-05", "Active")), row("View", "Rollback", "Export"));
                p.panels = panels(
                        panel("Model Health",
                                row("Status", s.get("modelStatus", "Online")),
                                row("Last Prediction", s.get("lastPrediction", "No predictions yet")),
                                row("Avg Response Time", s.get("avgProcessingTime", "0 sec")),
                                row("Error Rate", s.get("failedPredictionRate", "0%")),
                                row("Active Model", s.get("activeModel", "v1.1")))
                );
                break;
            case "reports":
                p.cards = rows(
                        row("Monthly Report", s.get("monthlyReport", "Ready"), "Current month"),
                        row("User Report", s.get("userReport", "Ready"), s.get("totalUsers", "0") + " users"),
                        row("AI Report", s.get("aiReport", "Ready"), s.get("totalAnalyses", "0") + " scans"),
                        row("Dataset Report", s.get("datasetReport", "Ready"), s.get("datasetImages", "0") + " images"),
                        row("CSV Export", "Live", "Data table"),
                        row("PDF Export", "Queued", "Summary")
                );
                break;
            case "news-manager":
                p.cards = rows(
                        row("Total News", s.get("totalNews", "0"), "All articles"),
                        row("Published News", s.get("publishedNews", "0"), "Public"),
                        row("Draft News", s.get("draftNews", "0"), "In progress"),
                        row("Last Published", s.get("lastPublished", "-"), "Latest"),
                        row("Most Viewed", s.get("mostViewedNews", "No data"), "Top article"),
                        row("Create News", "+", "New article")
                );
                p.table = new Table("News Articles", row("ID", "Title", "Status", "Date"), s.matrix("newsRows", row("-", "No news", "-", "-")), row("Edit", "Preview", "Publish", "Delete"));
                break;
            case "activity-logs":
                p.cards = rows(
                        row("Today Logs", s.get("todayLogs", "0"), "Today"),
                        row("Admin Actions", s.get("adminActions", "0"), "Control events"),
                        row("Errors", s.get("errorLogs", "0"), "Need review"),
                        row("Uploads", s.get("todayAnalyses", "0"), "Today"),
                        row("Logins", s.get("activeUsers", "0"), "Active users"),
                        row("System", s.get("modelStatus", "Online"), "Status")
                );
                p.table = new Table("Activity Logs", row("Time", "User", "Action", "Status"), s.matrix("activityRows", row("-", "System", "No logs", "-")), row("Open", "Export"));
                break;
            case "messages":
                p.cards = rows(
                        row("Total", s.get("totalMessages", "0"), "Messages"),
                        row("Unread", s.get("unreadMessages", "0"), "Need response"),
                        row("Replied", s.get("repliedMessages", "0"), "Handled"),
                        row("Pending", s.get("pendingMessages", "0"), "Open"),
                        row("Today", s.get("unreadMessages", "0"), "New"),
                        row("Avg Reply", "2h", "Response")
                );
                p.table = new Table("User Messages", row("ID", "Name", "Subject", "Status"), s.matrix("messagesRows", row("-", "No messages", "-", "-")), row("Open", "Reply", "Mark Read", "Delete"));
                break;
            case "settings":
                p.panels = panels(
                        panel("General Settings",
                                row("Site Name", s.get("siteName", "EndoScan AI")),
                                row("Public Stats", s.get("publicStats", "ON")),
                                row("Registration", s.get("registration", "ON")),
                                row("Maintenance Mode", s.get("maintenanceMode", "OFF"))),
                        panel("AI Settings",
                                row("Active Model", s.get("activeModel", "v1.1")),
                                row("Confidence Threshold", s.get("confidenceThreshold", "70%")),
                                row("Save Uploaded Images", s.get("saveUploadedImages", "ON"))),
                        panel("Security",
                                row("Admin Email", s.get("adminEmail", "admin@endoscan.ai")),
                                row("Two Factor Auth", s.get("twoFactorAuth", "OFF")),
                                row("Session Timeout", s.get("sessionTimeout", "30 min")))
                );
                break;
            case "user-detail":
                p.cards = rows(
                        row("Total Scans", s.get("totalAnalyses", "0"), "User analyses"),
                        row("Avg Confidence", s.get("averageConfidence", "0%"), "Mean score"),
                        row("High Risk", s.get("highRiskCases", "0"), "Serious"),
                        row("Last Login", "Today", "Active")
                );
                p.panels = panels(panel("Profile", s.matrix("userProfileItems", row("Email", "-"), row("Role", "-"), row("Status", "-"), row("Registered", "-"))));
                p.table = new Table("User Analysis History", row("Date", "Prediction", "Confidence", "Risk"), s.matrix("userHistoryRows", row("-", "No analyses", "-", "-")), row("Block User", "Reset Password", "Make Admin", "Delete Account"));
                break;
            case "analysis-detail":
                p.panels = panels(
                        panel("Uploaded Image", s.matrix("analysisImageItems", row("Preview", "No image"), row("Image", "-"))),
                        panel("AI Result", s.matrix("analysisResultItems", row("Prediction", "-"), row("Confidence", "-"), row("Risk Level", "-")))
                );
                p.notes = s.list("analysisNotes", row("Admin note: No analysis selected."));
                break;
            default:
                p.cards = rows(
                        row("Total Users", s.get("totalUsers", "0"), "Registered accounts"),
                        row("Total Analyses", s.get("totalAnalyses", "0"), "All analyses"),
                        row("Today Analyses", s.get("todayAnalyses", "0"), "Today"),
                        row("Average Confidence", s.get("averageConfidence", "0%"), "Model confidence"),
                        row("High Risk Cases", s.get("highRiskCases", "0"), "Need review"),
                        row("Dataset Images", s.get("datasetImages", "0"), "Images")
                );
                p.charts = charts(
                        chart("Analyses Last 7 Days", "line", s.matrix("chartLast7Days", row("Today", "0"))),
                        chart("Risk Distribution", "bars", s.matrix("chartRiskDistribution", row("Low", "0"), row("Medium", "0"), row("High", "0")))
                );
                p.table = new Table("Recent Analyses", row("User", "Prediction", "Confidence", "Risk"), s.matrix("recentAnalysesRows", row("-", "No data", "-", "-")), row("Open Detail"));
                p.panels = panels(
                        panel("System Alerts",
                                row("Low-confidence analyses", s.get("lowConfidenceCases", "0") + " need review"),
                                row("Failed image uploads today", s.get("failedUploadsToday", "0")),
                                row("Model response time", s.get("modelResponseDelta", "Stable")),
                                row("Dataset status", s.get("datasetStatus", "Healthy"))),
                        panel("Model Health",
                                row("Status", s.get("modelStatus", "Online")),
                                row("Last Prediction", s.get("lastPrediction", "No predictions yet")),
                                row("Avg Response Time", s.get("avgProcessingTime", "0 sec")),
                                row("Error Rate", s.get("failedPredictionRate", "0%")),
                                row("Active Model", s.get("activeModel", "v1.1"))),
                        panel("Storage Usage",
                                row("Uploaded Images", s.get("uploadedImages", "0")),
                                row("Storage Used", s.get("storageUsed", "0 B")),
                                row("Average Image Size", s.get("averageImageSize", "0 B")),
                                row("Old Files Cleanup", s.get("oldFilesCleanup", "Enabled")))
                );
                p.notifications = s.list("notifications", row("Dataset status: healthy"));
                break;
        }
    }

    private static Page userPage(String section, String userId) {
        String[] meta = metaFor(USER_META, section, "snapshot");
        Page p = new Page("user", meta[0], meta[1], meta[2], meta[3]);
        Snapshot snapshot = Snapshot.load(userId);

        switch (p.section) {
            case "scan-library":
                p.filters = row("Date", "Prediction", "Risk", "Confidence");
                p.table = new Table("Saved Analyses", row("Date", "Prediction", "Confidence", "Risk"), rows(
                        row("2026-05-17", "Normal", "94%", "Low"),
                        row("2026-05-14", "Polyps", "88%", "Medium"),
                        row("2026-05-10", "Esophagitis", "83%", "Medium")
                ), row("Open Detail", "Download Result", "Delete"));
                p.detailTarget = "/dashboard/analysis-detail";
                p.cards = rows(row("My Scan Count", "24", "+7 this month"), row("Saved", "24 results", "Library"), row("Latest Check", "Normal", "94% confidence"));
                break;
            case "ai-insights":
                p.cards = rows(row("Most Common Result", "Normal", "62% of analyses"), row("Result Balance", "62 / 38", "Normal / abnormal"), row("Review Need", "3 cases", "Below confidence threshold"));
                p.charts = charts(chart("Result Balance", "bars", row("Normal", "62"), row("Abnormal", "38")), chart("Top Predictions", "bars", row("Normal", "15"), row("Polyps", "4"), row("Esophagitis", "3")));
                p.panels = panels(panel("AI-assisted summary", row("Most common result", "Normal"), row("Normal analyses", "62%"), row("Trend", "Low-risk trend across last 5 analyses")));
                p.notes = row("Your average confidence is stable.", "3 results may need professional review.", "Your last 5 analyses show a low-risk trend.");
                break;
            case "risk-map":
                p.cards = rows(row("Low Risk", "15", "Stable"), row("Medium Risk", "7", "Watch"), row("High Risk", "2", "Review"));
                p.charts = charts(chart("Risk Distribution", "bars", row("Low", "62"), row("Medium", "29"), row("High", "9")));
                p.panels = panels(panel("Review Needed", row("Analyses", "3"), row("Reason", "Confidence below 70%"), row("Action", "View cases")));
                p.table = new Table("Risk Cases", row("Date", "Prediction", "Confidence", "Risk"), rows(row("2026-05-14", "Polyps", "88%", "Medium"), row("2026-05-09", "Ulcerative", "76%", "High")), row("View Cases"));
                break;
            case "confidence-pulse":
                p.cards = rows(row("Avg Conf.", "89%", "Across analyses"), row("Highest", "97%", "Best case"), row("Low Conf.", "3 cases", "Need review"));
                p.charts = charts(chart("Confidence Trend", "line", row("May 01", "82"), row("May 04", "88"), row("May 07", "61"), row("May 10", "83"), row("May 14", "88"), row("May 17", "94")));
                p.table = new Table("Low Confidence Cases", row("Date", "Prediction", "Confidence", "Action"), rows(row("2026-05-07", "Normal", "61%", "Review"), row("2026-05-02", "Polyps", "66%", "Review")), row("Review"));
                break;
            case "timeline":
                p.filters = row("7 days", "30 days", "All");
                p.timeline = rows(row("May 17, 2026", "Normal", "94% confidence - Low risk"), row("May 14, 2026", "Polyps", "88% confidence - Medium risk"), row("May 10, 2026", "Esophagitis", "83% confidence - Medium risk"));
                p.charts = charts(chart("Monthly Activity", "bars", row("Week 1", "3"), row("Week 2", "6"), row("Week 3", "4"), row("Week 4", "9")));
                break;
            case "reports":
                p.cards = rows(row("Total Reports", "24", "Generated"), row("Downloaded", "12", "Downloads"), row("Latest", "2026-05-17", "Newest report"));
                p.form = new Form("Report Builder", rows(row("Report Type", "Single Analysis"), row("Date Range", "2026-05-01 to 2026-05-17"), row("Format", "PDF / CSV")), row("Prediction result", "Confidence score", "Risk level", "AI disclaimer"), row("Generate Report", "Download Latest PDF"));
                break;
            case "profile":
                p.cards = rows(row("Username", "Akmal", "Profile"), row("Saved Scans", "24", "Library"), row("Account", "Active", "Status"));
                p.panels = panels(panel("Profile", row("Username", "Akmal"), row("Email", "akmal@mail.com"), row("Status", "Active"), row("Joined", "2026-05-01")));
                p.actions = row("Edit Profile", "Change Password", "Logout");
                break;
            case "analysis-detail":
                p.panels = panels(
                        panel("Uploaded Image", row("Preview", "image preview"), row("Source", "Saved scan")),
                        panel("AI Result", row("Prediction", "Polyps"), row("Confidence", "88%"), row("Risk Level", "Medium"), row("Date", "2026-05-14"), row("Processing Time", "2.1 sec"))
                );
                p.notes = row("AI Note: This result is an AI-assisted suggestion. Please consult a specialist.");
                p.actions = row("Download PDF", "Back to Library");
                break;
            default:
                p.cards = rows(
                        row("My Scans", "24", "+7 this month", "/dashboard/scan-library"),
                        row("Latest Check", "Normal", "94% confidence", "/dashboard/analysis-detail"),
                        row("Confidence Pulse", "89%", "Stable trend", "/dashboard/confidence-pulse"),
                        row("Risk Map", "Low", "3 need review", "/dashboard/risk-map"),
                        row("Result Balance", "62 / 38", "Normal / abnormal", "/dashboard/ai-insights"),
                        row("AI Notes", "4 notes", "Open summary", "/dashboard/ai-insights")
                );
                p.charts = charts(
                        chart("Confidence Pulse", "line", row("May 01", "82"), row("May 04", "88"), row("May 07", "61"), row("May 10", "83"), row("May 14", "88"), row("May 17", "94")),
                        chart("Result Balance", "bars", row("Normal", "62"), row("Abnormal", "38"))
                );
                p.panels = panels(panel("Latest Analysis", row("Prediction", "Normal"), row("Confidence", "94%"), row("Risk Level", "Low"), row("Date", "2026-05-17")));
                p.notes = row("Your latest result is low risk.", "Your average confidence is 89%.", "3 analyses have confidence below 70%.", "Consider reviewing medium/high risk results with a specialist.");
                break;
        }
        applyUserSnapshot(p, snapshot);
        return p;
    }

    private static void applyUserSnapshot(Page p, Snapshot s) {
        if (!s.hasData()) return;

        switch (p.section) {
            case "scan-library":
                p.cards = rows(
                        row("My Scan Count", s.get("userScanCount", "0"), s.get("userThisMonth", "0 scans")),
                        row("Saved", s.get("userSavedResults", "0 results"), "Library"),
                        row("Latest Check", s.get("userLatestCheck", "No scans"), s.get("userLatestConfidence", "No confidence yet"))
                );
                p.table = new Table("Saved Analyses", row("Date", "Prediction", "Confidence", "Risk"), s.matrix("userScanRows", row("-", "No saved analyses", "-", "-")), row("Open Detail", "Download Result", "Delete"));
                p.detailTarget = "/dashboard/analysis-detail";
                break;
            case "ai-insights":
                p.cards = rows(
                        row("Most Common Result", s.get("userMostCommonResult", "No data"), s.get("userMostCommonPercent", "0%") + " of analyses"),
                        row("Result Balance", s.get("userResultBalance", "0 / 0"), "Normal / abnormal"),
                        row("Review Need", s.get("userReviewNeed", "0 cases"), "Needs closer review")
                );
                p.charts = charts(
                        chart("Result Balance", "bars", s.matrix("userChartResultBalance", row("Normal", "0"), row("Abnormal", "0"))),
                        chart("Top Predictions", "bars", s.matrix("userChartTopPredictions", row("No data", "0")))
                );
                p.panels = panels(panel("AI-assisted summary", s.matrix("userInsightPanel", row("Summary", "No saved analyses yet"))));
                p.notes = s.list("userAiNotes", row("Upload your first image to start insights."));
                break;
            case "risk-map":
                p.cards = rows(
                        row("Low Risk", riskCount(s, "Low"), "Stable"),
                        row("Medium Risk", riskCount(s, "Medium"), "Watch"),
                        row("High Risk", riskCount(s, "High"), "Review")
                );
                p.charts = charts(chart("Risk Distribution", "bars", s.matrix("userChartRiskDistribution", row("Low", "0"), row("Medium", "0"), row("High", "0"))));
                p.panels = panels(panel("Review Needed", row("Analyses", s.get("userReviewNeed", "0 cases")), row("Reason", "Low confidence or high risk"), row("Action", "View cases")));
                p.table = new Table("Risk Cases", row("Date", "Prediction", "Confidence", "Risk"), s.matrix("userRiskRows", row("-", "No risk cases", "-", "-")), row("View Cases"));
                p.detailTarget = "/dashboard/analysis-detail";
                break;
            case "confidence-pulse":
                p.cards = rows(
                        row("Avg Conf.", s.get("userAvgConfidence", "0%"), "Across analyses"),
                        row("Highest", s.get("userHighestConfidence", "0%"), "Best case"),
                        row("Low Conf.", s.get("userLowConfidenceCases", "0 cases"), "Need review")
                );
                p.charts = charts(chart("Confidence Trend", "line", s.matrix("userChartConfidenceTrend", row("No data", "0"))));
                p.table = new Table("Low Confidence Cases", row("Date", "Prediction", "Confidence", "Action"), s.matrix("userLowConfidenceRows", row("-", "No low confidence cases", "-", "-")), row("Review"));
                p.detailTarget = "/dashboard/analysis-detail";
                break;
            case "timeline":
                p.timeline = s.matrix("userTimelineRows", row("-", "No analyses yet", "Upload an image to start your timeline"));
                p.charts = charts(chart("Monthly Activity", "bars", s.matrix("userChartMonthlyActivity", row("Week 1", "0"), row("Week 2", "0"), row("Week 3", "0"), row("Week 4", "0"))));
                break;
            case "reports":
                p.cards = rows(
                        row("Total Reports", s.get("userTotalReports", "0"), "Generated"),
                        row("Downloaded", s.get("userDownloadedReports", "0"), "Downloads"),
                        row("Latest", s.get("userLatestReport", "-"), "Newest report")
                );
                p.form = new Form(
                        "Report Builder",
                        s.matrix("userReportFields", row("Report Type", "Single Analysis"), row("Date Range", "-"), row("Format", "PDF / CSV")),
                        row("Prediction result", "Confidence score", "Risk level", "AI disclaimer"),
                        row("Generate Report", "Download Latest PDF")
                );
                break;
            case "profile":
                p.cards = rows(
                        row("Username", s.get("userUsername", "User"), "Profile"),
                        row("Saved Scans", s.get("userScanCount", "0"), "Library"),
                        row("Account", s.get("userStatus", "-"), "Status")
                );
                p.panels = panels(panel("Profile", s.matrix("userProfilePanel", row("Email", "-"), row("Role", "-"), row("Status", "-"), row("Registered", "-"))));
                break;
            case "analysis-detail":
                p.panels = panels(
                        panel("Uploaded Image", s.matrix("userAnalysisImageItems", row("Preview", "No image"), row("Image", "-"))),
                        panel("AI Result", s.matrix("userAnalysisResultItems", row("Prediction", "-"), row("Confidence", "-"), row("Risk Level", "-")))
                );
                p.notes = s.list("userAnalysisNotes", row("AI Note: No saved analysis is selected yet."));
                break;
            default:
                p.cards = rows(
                        row("My Scans", s.get("userScanCount", "0"), s.get("userThisMonth", "0 scans"), "/dashboard/scan-library"),
                        row("Latest Check", s.get("userLatestCheck", "No scans"), s.get("userLatestConfidence", "No confidence yet"), "/dashboard/analysis-detail"),
                        row("Confidence Pulse", s.get("userAvgConfidence", "0%"), "Stable trend", "/dashboard/confidence-pulse"),
                        row("Risk Map", s.get("userRiskLevel", "No data"), s.get("userReviewNeed", "0 cases") + " need review", "/dashboard/risk-map"),
                        row("Result Balance", s.get("userResultBalance", "0 / 0"), "Normal / abnormal", "/dashboard/ai-insights"),
                        row("AI Notes", "Personal summary", "Open insights", "/dashboard/ai-insights")
                );
                p.charts = charts(
                        chart("Confidence Pulse", "line", s.matrix("userChartConfidenceTrend", row("No data", "0"))),
                        chart("Result Balance", "bars", s.matrix("userChartResultBalance", row("Normal", "0"), row("Abnormal", "0")))
                );
                p.panels = panels(
                        panel("Latest Analysis", s.matrix("userLatestPanel", row("Prediction", "No scans yet"), row("Confidence", "-"), row("Risk Level", "-"), row("Date", "-"))),
                        panel("AI Notes", aiNotesRows(s)),
                        panel("This Month", row("Scans", s.get("userThisMonth", "0 scans")), row("Latest", s.get("userLatestCheck", "No scans"))),
                        panel("Review Need", row("Cases", s.get("userReviewNeed", "0 cases")), row("Reason", "Low confidence or high risk"))
                );
                p.notes = new String[0];
                break;
        }
    }

    private static String riskCount(Snapshot s, String risk) {
        switch (risk) {
            case "High":
                return s.get("userHighRiskCount", "0");
            case "Medium":
                return s.get("userMediumRiskCount", "0");
            default:
                return s.get("userLowRiskCount", "0");
        }
    }

    private static String[][] aiNotesRows(Snapshot s) {
        String[] notes = s.list("userAiNotes", row("Upload your first image to start insights."));
        String[][] rows = new String[notes.length][];
        for (int i = 0; i < notes.length; i++) {
            rows[i] = row("Note " + (i + 1), notes[i]);
        }
        return rows;
    }

    private static String buildPayload(Page p) {
        StringBuilder json = new StringBuilder();
        json.append("{");
        prop(json, "scope", p.scope).append(",");
        prop(json, "section", p.section).append(",");
        prop(json, "title", p.title).append(",");
        prop(json, "subtitle", p.subtitle).append(",");
        prop(json, "searchPlaceholder", p.searchPlaceholder).append(",");
        appendCards(json, p.cards).append(",");
        appendCharts(json, p.charts).append(",");
        appendTable(json, p.table).append(",");
        array(json, "notes", p.notes).append(",");
        array(json, "filters", p.filters).append(",");
        array(json, "actions", p.actions).append(",");
        array(json, "notifications", p.notifications).append(",");
        appendPanels(json, p.panels).append(",");
        appendTimeline(json, p.timeline).append(",");
        appendForm(json, p.form).append(",");
        prop(json, "detailTarget", p.detailTarget);
        json.append("}");
        return json.toString();
    }

    private static StringBuilder appendCards(StringBuilder json, String[][] cards) {
        json.append("\"cards\":[");
        for (int i = 0; i < cards.length; i++) {
            if (i > 0) json.append(",");
            json.append("{");
            prop(json, "label", cards[i][0]).append(",");
            prop(json, "value", cards[i][1]).append(",");
            prop(json, "detail", cards[i][2]);
            if (cards[i].length > 3) {
                json.append(",");
                prop(json, "target", cards[i][3]);
            }
            json.append("}");
        }
        json.append("]");
        return json;
    }

    private static StringBuilder appendCharts(StringBuilder json, Chart[] charts) {
        json.append("\"charts\":[");
        for (int i = 0; i < charts.length; i++) {
            if (i > 0) json.append(",");
            Chart chart = charts[i];
            json.append("{");
            prop(json, "title", chart.title).append(",");
            prop(json, "type", chart.type).append(",");
            json.append("\"items\":[");
            for (int j = 0; j < chart.items.length; j++) {
                if (j > 0) json.append(",");
                json.append("[");
                quote(json, chart.items[j][0]);
                json.append(",");
                quote(json, chart.items[j][1]);
                json.append("]");
            }
            json.append("]}");
        }
        json.append("]");
        return json;
    }

    private static StringBuilder appendTable(StringBuilder json, Table table) {
        json.append("\"table\":");
        if (table == null) {
            json.append("null");
            return json;
        }
        json.append("{");
        prop(json, "title", table.title).append(",");
        array(json, "columns", table.columns).append(",");
        json.append("\"rows\":[");
        for (int i = 0; i < table.rows.length; i++) {
            if (i > 0) json.append(",");
            json.append("[");
            for (int j = 0; j < table.rows[i].length; j++) {
                if (j > 0) json.append(",");
                quote(json, table.rows[i][j]);
            }
            json.append("]");
        }
        json.append("],");
        array(json, "actions", table.actions);
        json.append("}");
        return json;
    }

    private static StringBuilder appendPanels(StringBuilder json, Panel[] panels) {
        json.append("\"panels\":[");
        for (int i = 0; i < panels.length; i++) {
            if (i > 0) json.append(",");
            Panel panel = panels[i];
            json.append("{");
            prop(json, "title", panel.title).append(",");
            json.append("\"items\":[");
            for (int j = 0; j < panel.items.length; j++) {
                if (j > 0) json.append(",");
                json.append("[");
                quote(json, panel.items[j][0]);
                json.append(",");
                quote(json, panel.items[j][1]);
                json.append("]");
            }
            json.append("]}");
        }
        json.append("]");
        return json;
    }

    private static StringBuilder appendTimeline(StringBuilder json, String[][] timeline) {
        json.append("\"timeline\":[");
        for (int i = 0; i < timeline.length; i++) {
            if (i > 0) json.append(",");
            json.append("{");
            prop(json, "date", timeline[i][0]).append(",");
            prop(json, "title", timeline[i][1]).append(",");
            prop(json, "detail", timeline[i][2]);
            json.append("}");
        }
        json.append("]");
        return json;
    }

    private static StringBuilder appendForm(StringBuilder json, Form form) {
        json.append("\"form\":");
        if (form == null) {
            json.append("null");
            return json;
        }
        json.append("{");
        prop(json, "title", form.title).append(",");
        json.append("\"fields\":[");
        for (int i = 0; i < form.fields.length; i++) {
            if (i > 0) json.append(",");
            json.append("[");
            quote(json, form.fields[i][0]);
            json.append(",");
            quote(json, form.fields[i][1]);
            json.append("]");
        }
        json.append("],");
        array(json, "included", form.included).append(",");
        array(json, "actions", form.actions);
        json.append("}");
        return json;
    }

    private static StringBuilder array(StringBuilder json, String key, String[] values) {
        quote(json, key);
        json.append(":[");
        for (int i = 0; i < values.length; i++) {
            if (i > 0) json.append(",");
            quote(json, values[i]);
        }
        json.append("]");
        return json;
    }

    private static String[] metaFor(String[][] menu, String section, String fallback) {
        for (String[] item : menu) {
            if (item[0].equals(section)) return item;
        }
        for (String[] item : menu) {
            if (item[0].equals(fallback)) return item;
        }
        return menu[0];
    }

    private static String[] row(String... values) {
        return values;
    }

    private static String[][] rows(String[]... values) {
        return values;
    }

    private static Chart chart(String title, String type, String[]... items) {
        return new Chart(title, type, rows(items));
    }

    private static Chart[] charts(Chart... charts) {
        return charts;
    }

    private static Panel panel(String title, String[]... items) {
        return new Panel(title, rows(items));
    }

    private static Panel[] panels(Panel... panels) {
        return panels;
    }

    private static StringBuilder prop(StringBuilder json, String key, String value) {
        quote(json, key);
        json.append(":");
        quote(json, value == null ? "" : value);
        return json;
    }

    private static void quote(StringBuilder json, String value) {
        json.append("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '"' || c == '\\') {
                json.append("\\").append(c);
            } else if (c == '\n') {
                json.append("\\n");
            } else {
                json.append(c);
            }
        }
        json.append("\"");
    }

    private static void send(HttpExchange exchange, int status, String body) throws IOException {
        addCors(exchange);
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        Headers headers = exchange.getResponseHeaders();
        headers.set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(bytes);
        }
    }

    private static void addCors(HttpExchange exchange) {
        Headers headers = exchange.getResponseHeaders();
        headers.set("Access-Control-Allow-Origin", "*");
        headers.set("Access-Control-Allow-Methods", "GET, OPTIONS");
        headers.set("Access-Control-Allow-Headers", "Content-Type, Accept");
    }

    private static String queryValue(HttpExchange exchange, String key) {
        String query = exchange.getRequestURI().getRawQuery();
        if (query == null || query.isEmpty()) {
            return "";
        }
        String[] pairs = query.split("&");
        for (String pair : pairs) {
            int index = pair.indexOf('=');
            String rawKey = index >= 0 ? pair.substring(0, index) : pair;
            if (!key.equals(urlDecode(rawKey))) {
                continue;
            }
            return urlDecode(index >= 0 ? pair.substring(index + 1) : "");
        }
        return "";
    }

    private static String urlDecode(String value) {
        try {
            return URLDecoder.decode(value, StandardCharsets.UTF_8);
        } catch (IllegalArgumentException ex) {
            return "";
        }
    }

    private static final class Snapshot {
        private final Map<String, String> values;

        private Snapshot(Map<String, String> values) {
            this.values = values;
        }

        static Snapshot load() {
            return load("");
        }

        static Snapshot load(String userId) {
            HttpURLConnection conn = null;
            try {
                String target = PYTHON_STATS_BASE_URL + "/api/internal/stats-snapshot";
                if (userId != null && !userId.isBlank()) {
                    target += "?user_id=" + URLEncoder.encode(userId, StandardCharsets.UTF_8);
                }
                URL url = new URL(target);
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(900);
                conn.setReadTimeout(1600);
                conn.setRequestProperty("Accept", "application/json");
                conn.setRequestProperty("X-Internal-Stats-Key", INTERNAL_STATS_KEY);
                if (conn.getResponseCode() != 200) {
                    return empty();
                }
                try (InputStream input = conn.getInputStream()) {
                    String body = new String(input.readAllBytes(), StandardCharsets.UTF_8);
                    return new Snapshot(parseFlatJson(body));
                }
            } catch (Exception ignored) {
                return empty();
            } finally {
                if (conn != null) {
                    conn.disconnect();
                }
            }
        }

        static Snapshot empty() {
            return new Snapshot(new HashMap<>());
        }

        boolean hasData() {
            return !values.isEmpty();
        }

        String get(String key, String fallback) {
            String encoded = values.get(key);
            if (encoded == null || encoded.isEmpty()) {
                return fallback;
            }
            try {
                return new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8);
            } catch (IllegalArgumentException ex) {
                return fallback;
            }
        }

        String[] list(String key, String[] fallback) {
            String value = get(key, "");
            if (value.isEmpty()) {
                return fallback;
            }
            return value.split(ROW_SEP, -1);
        }

        String[][] matrix(String key, String[]... fallback) {
            String value = get(key, "");
            if (value.isEmpty()) {
                return fallback;
            }
            String[] rowParts = value.split(ROW_SEP, -1);
            String[][] rows = new String[rowParts.length][];
            for (int i = 0; i < rowParts.length; i++) {
                rows[i] = rowParts[i].split(CELL_SEP, -1);
            }
            return rows;
        }

        private static Map<String, String> parseFlatJson(String json) {
            Map<String, String> parsed = new HashMap<>();
            int[] index = {0};
            skipWhitespace(json, index);
            if (index[0] >= json.length() || json.charAt(index[0]) != '{') {
                return parsed;
            }
            index[0]++;
            while (index[0] < json.length()) {
                skipWhitespace(json, index);
                if (index[0] < json.length() && json.charAt(index[0]) == '}') {
                    break;
                }
                if (index[0] >= json.length() || json.charAt(index[0]) != '"') {
                    break;
                }
                String key = parseJsonString(json, index);
                skipWhitespace(json, index);
                if (index[0] >= json.length() || json.charAt(index[0]) != ':') {
                    break;
                }
                index[0]++;
                skipWhitespace(json, index);
                String value;
                if (index[0] < json.length() && json.charAt(index[0]) == '"') {
                    value = parseJsonString(json, index);
                } else {
                    int start = index[0];
                    while (index[0] < json.length() && json.charAt(index[0]) != ',' && json.charAt(index[0]) != '}') {
                        index[0]++;
                    }
                    value = json.substring(start, index[0]).trim();
                }
                parsed.put(key, value);
                skipWhitespace(json, index);
                if (index[0] < json.length() && json.charAt(index[0]) == ',') {
                    index[0]++;
                }
            }
            return parsed;
        }

        private static String parseJsonString(String json, int[] index) {
            StringBuilder out = new StringBuilder();
            index[0]++;
            while (index[0] < json.length()) {
                char c = json.charAt(index[0]++);
                if (c == '"') {
                    break;
                }
                if (c == '\\' && index[0] < json.length()) {
                    char escaped = json.charAt(index[0]++);
                    switch (escaped) {
                        case '"':
                        case '\\':
                        case '/':
                            out.append(escaped);
                            break;
                        case 'b':
                            out.append('\b');
                            break;
                        case 'f':
                            out.append('\f');
                            break;
                        case 'n':
                            out.append('\n');
                            break;
                        case 'r':
                            out.append('\r');
                            break;
                        case 't':
                            out.append('\t');
                            break;
                        case 'u':
                            if (index[0] + 4 <= json.length()) {
                                String hex = json.substring(index[0], index[0] + 4);
                                try {
                                    out.append((char) Integer.parseInt(hex, 16));
                                } catch (NumberFormatException ignored) {
                                    out.append("\\u").append(hex);
                                }
                                index[0] += 4;
                            }
                            break;
                        default:
                            out.append(escaped);
                            break;
                    }
                } else {
                    out.append(c);
                }
            }
            return out.toString();
        }

        private static void skipWhitespace(String json, int[] index) {
            while (index[0] < json.length() && Character.isWhitespace(json.charAt(index[0]))) {
                index[0]++;
            }
        }
    }

    private static final class Page {
        final String scope;
        final String section;
        final String title;
        final String subtitle;
        final String searchPlaceholder;
        String[][] cards = new String[0][0];
        Chart[] charts = new Chart[0];
        Table table;
        String[] notes = new String[0];
        String[] filters = new String[0];
        String[] actions = new String[0];
        String[] notifications = new String[0];
        Panel[] panels = new Panel[0];
        String[][] timeline = new String[0][0];
        Form form;
        String detailTarget = "";

        Page(String scope, String section, String title, String subtitle, String searchPlaceholder) {
            this.scope = scope;
            this.section = section;
            this.title = title;
            this.subtitle = subtitle;
            this.searchPlaceholder = searchPlaceholder;
        }
    }

    private static final class Chart {
        final String title;
        final String type;
        final String[][] items;

        Chart(String title, String type, String[][] items) {
            this.title = title;
            this.type = type;
            this.items = items;
        }
    }

    private static final class Table {
        final String title;
        final String[] columns;
        final String[][] rows;
        final String[] actions;

        Table(String title, String[] columns, String[][] rows, String[] actions) {
            this.title = title;
            this.columns = columns;
            this.rows = rows;
            this.actions = actions;
        }
    }

    private static final class Panel {
        final String title;
        final String[][] items;

        Panel(String title, String[][] items) {
            this.title = title;
            this.items = items;
        }
    }

    private static final class Form {
        final String title;
        final String[][] fields;
        final String[] included;
        final String[] actions;

        Form(String title, String[][] fields, String[] included, String[] actions) {
            this.title = title;
            this.fields = fields;
            this.included = included;
            this.actions = actions;
        }
    }
}
