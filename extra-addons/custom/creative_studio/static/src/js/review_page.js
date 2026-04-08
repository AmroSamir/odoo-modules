/** @odoo-module **/
import { Component, useState, useRef, onWillStart, onMounted, onPatched, onWillUnmount, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const DRAWING_COLORS = [
    { value: "#EF4444", name: "Red" },
    { value: "#22C55E", name: "Green" },
    { value: "#3B82F6", name: "Blue" },
    { value: "#8B5CF6", name: "Purple" },
    { value: "#F59E0B", name: "Yellow" },
    { value: "#F97316", name: "Orange" },
];

const ZOOM_LEVELS = [25, 50, 75, 100, 150, 200];

class ProofingReviewPage extends Component {
    static template = "creative_studio.ReviewPage";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.videoRef = useRef("videoPlayer");
        this.imageRef = useRef("imagePreview");
        this.imageContainerRef = useRef("imageContainer");
        this.svgOverlayRef = useRef("svgOverlay");
        this.fileInputRef = useRef("fileInput");
        this.commentRef = useRef("commentTextarea");
        this.hoverCursorRef = useRef("hoverCursor");

        this.state = useState({
            project: null,
            files: [],
            currentFile: null,
            currentVersion: null,
            annotations: [],
            newComment: "",
            loading: true,
            sidebarOpen: true,
            myDecision: null,
            fileReviews: [],
            // Annotation mode
            pinMode: false,
            pendingPin: null,
            // Reply state
            expandedAnnotations: {},
            replyTexts: {},
            // Highlight
            highlightedAnnotation: null,
            // Video timeline
            videoDuration: 0,
            // Filter
            showResolved: false,
            // Voice recording
            isRecording: false,
            recordingDuration: 0,
            hasVoiceMessage: false,
            // File attachments
            pendingAttachments: [],
            // @Mentions
            members: [],
            mentionActive: false,
            mentionQuery: "",
            mentionIndex: 0,
            // ─── Phase 5: Drawing tools ──────────────────
            drawingTool: null,
            drawingColor: "#22C55E",
            pendingDrawings: [],
            isDrawing: false,
            activeShape: null,
            // Canvas controls
            canvasRotation: 0,
            zoomLevel: 100,
            hideMarkers: false,
            viewMode: "view",
            // Comment visibility
            commentVisibility: "everyone",
            // Annotation counts
            annotationCounts: { resolved: 0, total: 0 },
            // UI dropdowns
            colorPickerOpen: false,
            zoomDropdownOpen: false,
            visibilityMenuOpen: false,
            // Hover cursor
            hoverCursorVisible: false,
            hoverCursorX: 0,
            hoverCursorY: 0,
        });

        this.projectId = this.props.action?.params?.project_id
            || this.props.action?.context?.project_id;
        this.fileId = this.props.action?.params?.file_id
            || this.props.action?.context?.file_id;
        this.stepId = this.props.action?.params?.step_id
            || this.props.action?.context?.step_id || null;
        this.versionId = this.props.action?.params?.version_id
            || this.props.action?.context?.version_id || null;

        // Voice recording internals (not reactive)
        this._mediaRecorder = null;
        this._audioChunks = [];
        this._audioBlob = null;
        this._audioUrl = null;
        this._recordingTimer = null;

        // Mention tracking
        this._pendingMentions = [];

        // Drawing internals
        this._undoStack = [];
        this._drawStartPoint = null;

        // Bound handler for global keydown
        this._onKeydownBound = this._onGlobalKeydown.bind(this);

        // Base image dimensions (measured at 100% zoom, no transform)
        this._baseImageWidth = 0;
        this._baseImageHeight = 0;

        onWillStart(async () => {
            if (this.fileId) {
                await this.loadData();
            }
        });

        onMounted(() => {
            this._setupVideoListeners();
            this._measureBaseImage();
            document.addEventListener("keydown", this._onKeydownBound);
            // No file ID (e.g. page refresh) — redirect back to projects
            if (!this.fileId) {
                this.action.doAction("creative_studio.proofing_project_action", { clearBreadcrumbs: true });
            }
        });

        onPatched(() => {
            this._setupVideoListeners();
            this._measureBaseImage();
        });

        onWillUnmount(() => {
            document.removeEventListener("keydown", this._onKeydownBound);
        });
    }

    // ─── Translations ─────────────────────────────────────
    _tr(key, fallback) {
        return (this._serverTranslations || {})[key] || fallback;
    }

    get T() {
        const s = this._serverTranslations || {};
        return s;
    }

    // ─── Static data ─────────────────────────────────────
    get drawingColors() { return DRAWING_COLORS; }
    get zoomLevels() { return ZOOM_LEVELS; }

    _markupAnnotations(annotations) {
        return annotations.map(ann => ({
            ...ann,
            body: ann.body ? markup(ann.body) : "",
            replies: (ann.replies || []).map(r => ({
                ...r,
                body: r.body ? markup(r.body) : "",
            })),
        }));
    }

    _measureBaseImage() {
        // Only measure when at 100% zoom (no scaling applied)
        if (this.state.zoomLevel !== 100) return;
        const img = this.imageRef.el;
        if (!img) return;
        if (img.complete && img.naturalWidth) {
            this._baseImageWidth = img.clientWidth;
            this._baseImageHeight = img.clientHeight;
        } else {
            // Image not loaded yet — listen for load
            img.addEventListener("load", () => {
                if (this.state.zoomLevel === 100) {
                    this._baseImageWidth = img.clientWidth;
                    this._baseImageHeight = img.clientHeight;
                }
            }, { once: true });
        }
    }

    _setupVideoListeners() {
        const vid = this.videoRef.el;
        if (vid) {
            vid.onloadedmetadata = () => {
                this.state.videoDuration = vid.duration;
            };
            if (vid.duration) {
                this.state.videoDuration = vid.duration;
            }
        }
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "proofing.file", "get_review_data", [this.fileId],
                { step_id: this.stepId, version_id: this.versionId }
            );
            this.state.project = data.project;
            this.state.files = data.files;
            this.state.currentFile = data.current_file;
            this.state.currentVersion = data.current_version;
            this.state.annotations = this._markupAnnotations(data.annotations);
            this.state.fileReviews = data.file_reviews;
            this.state.myDecision = data.my_decision;
            this.state.members = data.members || [];
            this.state.currentStep = data.current_step || null;
            this.state.annotationCounts = data.annotation_counts || { resolved: 0, total: 0 };
            this._serverTranslations = data.translations || {};
            this.state.pinMode = false;
            this.state.pendingPin = null;
            this.state.zoomLevel = 100;
            this._baseImageWidth = 0;
            this._baseImageHeight = 0;
            this._resetDrawingState();
        } catch (e) {
            this.notification.add(this._tr('failedToLoad', "Failed to load review data"), { type: "danger" });
        }
        this.state.loading = false;
    }

    get contentUrl() {
        if (!this.state.currentVersion) return "";
        return "/web/content/proofing.version/" + this.state.currentVersion.id + "/file_data/" + (this.state.currentVersion.filename || "file");
    }

    get isVideo() { return this.state.currentFile?.file_type === "video"; }
    get isImage() { return this.state.currentFile?.file_type === "image"; }
    get isPdf() { return this.state.currentFile?.file_type === "pdf"; }

    get filteredAnnotations() {
        if (this.state.showResolved) return this.state.annotations;
        return this.state.annotations.filter(a => !a.is_resolved);
    }

    get pointAnnotations() {
        const all = this.state.annotations.filter(
            a => a.annotation_type === "point" && !a.is_resolved
        );
        // When a comment is selected, only show THAT comment's pin
        const sel = this.state.highlightedAnnotation;
        if (sel !== null) {
            return all.filter(a => a.id === sel);
        }
        return all;
    }

    get timestampAnnotations() {
        const all = this.state.annotations.filter(
            a => a.annotation_type === "timestamp" && !a.is_resolved
        );
        const sel = this.state.highlightedAnnotation;
        if (sel !== null) {
            return all.filter(a => a.id === sel);
        }
        return all;
    }

    get annotationsWithDrawings() {
        return this.state.annotations.filter(
            a => a.drawing_data && a.drawing_data.length > 0
        );
    }

    // ─── @Mention suggestions ───────────────────────────
    get mentionSuggestions() {
        if (!this.state.mentionActive) return [];
        const q = this.state.mentionQuery.toLowerCase();
        return this.state.members.filter(
            m => m.name.toLowerCase().includes(q)
        ).slice(0, 5);
    }

    // ─── Sidebar ────────────────────────────────────────
    toggleSidebar() { this.state.sidebarOpen = !this.state.sidebarOpen; }

    async selectFile(file) {
        this.fileId = file.id;
        this.state.expandedAnnotations = {};
        this.state.replyTexts = {};
        this.state.highlightedAnnotation = null;
        this._clearVoiceRecording();
        this.state.pendingAttachments = [];
        this._resetDrawingState();
        await this.loadData();
    }

    isActiveFile(file) {
        return this.state.currentFile && file.id === this.state.currentFile.id;
    }

    // ─── Decisions ──────────────────────────────────────
    async onSetInReview() {
        if (this.state.myDecision) {
            await this.orm.call("proofing.review.decision", "action_set_in_review", [this.state.myDecision.id]);
            this.notification.add(this._tr('inReviewNotif', "Set to In Review"), { type: "info" });
            await this.loadData();
        }
    }

    async onApprove() {
        if (this.state.myDecision) {
            await this.orm.call("proofing.review.decision", "action_approve", [this.state.myDecision.id]);
            this.notification.add(this._tr('approvedNotif', "Approved!"), { type: "success" });
            await this.loadData();
        }
    }

    async onRequestChanges() {
        if (this.state.myDecision) {
            await this.orm.call("proofing.review.decision", "action_request_changes", [this.state.myDecision.id]);
            this.notification.add(this._tr('changesRequestedNotif', "Changes requested"), { type: "warning" });
            await this.loadData();
        }
    }

    async onRefuse() {
        if (this.state.myDecision) {
            await this.orm.call("proofing.review.decision", "action_refuse", [this.state.myDecision.id]);
            this.notification.add(this._tr('refusedNotif', "Refused"), { type: "danger" });
            await this.loadData();
        }
    }

    // ─── Pin Mode ───────────────────────────────────────
    togglePinMode() {
        this.state.pinMode = !this.state.pinMode;
        if (!this.state.pinMode) {
            this.state.pendingPin = null;
        }
    }

    onImageClick(ev) {
        // If a drawing tool is active, don't handle pin clicks here
        if (this.state.drawingTool) return;

        // If a comment is currently selected, deselect it first
        if (this.state.highlightedAnnotation !== null) {
            this.state.highlightedAnnotation = null;
            return;
        }

        // Use container rect — pins are positioned relative to container with left/top %
        const container = this.imageContainerRef.el;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        const rawX = ((ev.clientX - rect.left) / rect.width) * 100;
        const rawY = ((ev.clientY - rect.top) / rect.height) * 100;
        const { x, y } = this._compensateRotation(rawX, rawY);

        this.state.pendingPin = {
            x_percent: Math.max(0, Math.min(100, x)),
            y_percent: Math.max(0, Math.min(100, y)),
        };
        // Auto-enable pin mode on click
        this.state.pinMode = true;
        // Focus comment textarea
        setTimeout(() => {
            const ta = this.commentRef.el;
            if (ta) ta.focus();
        }, 50);
    }

    cancelPin() {
        this.state.pendingPin = null;
        this.state.pinMode = false;
    }

    // ─── Canvas Controls ────────────────────────────────
    onRotateLeft() {
        this.state.canvasRotation = (this.state.canvasRotation - 90 + 360) % 360;
    }

    onRotateRight() {
        this.state.canvasRotation = (this.state.canvasRotation + 90) % 360;
    }

    onZoomIn() {
        const idx = ZOOM_LEVELS.indexOf(this.state.zoomLevel);
        if (idx < ZOOM_LEVELS.length - 1) {
            this.state.zoomLevel = ZOOM_LEVELS[idx + 1];
        }
    }

    onZoomOut() {
        const idx = ZOOM_LEVELS.indexOf(this.state.zoomLevel);
        if (idx > 0) {
            this.state.zoomLevel = ZOOM_LEVELS[idx - 1];
        }
    }

    setZoomLevel(level) {
        this.state.zoomLevel = level;
        this.state.zoomDropdownOpen = false;
    }

    toggleZoomDropdown() {
        this.state.zoomDropdownOpen = !this.state.zoomDropdownOpen;
    }

    toggleHideMarkers() {
        this.state.hideMarkers = !this.state.hideMarkers;
    }

    setViewMode(mode) {
        this.state.viewMode = mode;
    }

    get imageContainerStyle() {
        const parts = [];
        const zoom = this.state.zoomLevel;
        if (zoom !== 100 && this._baseImageWidth > 0) {
            // Zoom by changing the actual container width (affects layout)
            // This ensures pins, scrollbars, and coordinates all use the same dimensions
            const w = Math.round(this._baseImageWidth * zoom / 100);
            parts.push("width: " + w + "px");
            parts.push("max-width: none");
            parts.push("max-height: none");
        }
        if (this.state.canvasRotation !== 0) {
            parts.push("transform: rotate(" + this.state.canvasRotation + "deg)");
        }
        return parts.join("; ");
    }

    // ─── Drawing Tools ──────────────────────────────────
    selectDrawingTool(tool) {
        if (this.state.drawingTool === tool) {
            this.state.drawingTool = null;
        } else {
            this.state.drawingTool = tool;
            // Don't clear pendingPin — pin and drawings coexist on the same comment
        }
    }

    selectColor(color) {
        this.state.drawingColor = color;
        this.state.colorPickerOpen = false;
    }

    toggleColorPicker() {
        this.state.colorPickerOpen = !this.state.colorPickerOpen;
    }

    setVisibility(vis) {
        this.state.commentVisibility = vis;
        this.state.visibilityMenuOpen = false;
    }

    toggleVisibilityMenu() {
        this.state.visibilityMenuOpen = !this.state.visibilityMenuOpen;
    }

    _resetDrawingState() {
        this.state.drawingTool = null;
        this.state.pendingDrawings = [];
        this.state.isDrawing = false;
        this.state.activeShape = null;
        this.state.commentVisibility = "everyone";
        this._undoStack = [];
        this._drawStartPoint = null;
    }

    _compensateRotation(rawX, rawY) {
        const r = this.state.canvasRotation;
        if (r === 90) return { x: rawY, y: 100 - rawX };
        if (r === 180) return { x: 100 - rawX, y: 100 - rawY };
        if (r === 270) return { x: 100 - rawY, y: rawX };
        return { x: rawX, y: rawY };
    }

    _svgPercentFromEvent(ev) {
        // Use container rect — SVG overlay and drawings are positioned relative to container
        const container = this.imageContainerRef.el;
        if (!container) return null;
        const rect = container.getBoundingClientRect();
        const rawX = ((ev.clientX - rect.left) / rect.width) * 100;
        const rawY = ((ev.clientY - rect.top) / rect.height) * 100;
        return this._compensateRotation(rawX, rawY);
    }

    onSvgMouseDown(ev) {
        if (!this.state.drawingTool) return;
        ev.preventDefault();
        ev.stopPropagation();
        const pt = this._svgPercentFromEvent(ev);
        if (!pt) return;

        this.state.isDrawing = true;
        this._drawStartPoint = pt;

        const tool = this.state.drawingTool;
        const color = this.state.drawingColor;

        if (tool === "freehand") {
            this.state.activeShape = { type: "freehand", color, points: [[pt.x, pt.y]] };
        } else if (tool === "rect") {
            this.state.activeShape = { type: "rect", color, x: pt.x, y: pt.y, w: 0, h: 0 };
        } else if (tool === "arrow" || tool === "line") {
            // Both arrow and line use start/end points; arrow gets a marker-end, line does not
            this.state.activeShape = { type: tool, color, x1: pt.x, y1: pt.y, x2: pt.x, y2: pt.y };
        }

        // Use document-level events so drawing continues even if mouse leaves SVG
        this._onDocMouseMove = this._onDrawingMouseMove.bind(this);
        this._onDocMouseUp = this._onDrawingMouseUp.bind(this);
        document.addEventListener("mousemove", this._onDocMouseMove);
        document.addEventListener("mouseup", this._onDocMouseUp);
    }

    _onDrawingMouseMove(ev) {
        if (!this.state.isDrawing || !this.state.activeShape) return;
        ev.preventDefault();
        const pt = this._svgPercentFromEvent(ev);
        if (!pt) return;

        const shape = this.state.activeShape;
        const tool = shape.type;

        if (tool === "freehand") {
            const pts = [...shape.points, [pt.x, pt.y]];
            this.state.activeShape = { ...shape, points: pts };
        } else if (tool === "rect") {
            const sx = this._drawStartPoint.x;
            const sy = this._drawStartPoint.y;
            this.state.activeShape = {
                ...shape,
                x: Math.min(sx, pt.x),
                y: Math.min(sy, pt.y),
                w: Math.abs(pt.x - sx),
                h: Math.abs(pt.y - sy),
            };
        } else if (tool === "arrow" || tool === "line") {
            this.state.activeShape = { ...shape, x2: pt.x, y2: pt.y };
        }
    }

    _onDrawingMouseUp(ev) {
        // Clean up document listeners
        document.removeEventListener("mousemove", this._onDocMouseMove);
        document.removeEventListener("mouseup", this._onDocMouseUp);

        if (!this.state.isDrawing || !this.state.activeShape) return;

        const shape = { ...this.state.activeShape };

        // Discard tiny shapes (accidental clicks)
        let isValid = true;
        if (shape.type === "freehand") {
            isValid = shape.points && shape.points.length > 2;
        } else if (shape.type === "rect") {
            isValid = shape.w > 0.5 && shape.h > 0.5;
        } else if (shape.type === "arrow" || shape.type === "line") {
            const dx = shape.x2 - shape.x1;
            const dy = shape.y2 - shape.y1;
            isValid = Math.sqrt(dx * dx + dy * dy) > 1;
        }

        if (isValid) {
            if (shape.type === "freehand" && shape.points.length > 5) {
                shape.points = this._simplifyPoints(shape.points, 0.3);
            }
            this._undoStack.push(shape);
            this.state.pendingDrawings = [...this.state.pendingDrawings, shape];
        }

        this.state.isDrawing = false;
        this.state.activeShape = null;
        this._drawStartPoint = null;
    }

    // Not used anymore — document events handle move/up
    onSvgMouseMove(ev) {}
    onSvgMouseUp(ev) {}

    _simplifyPoints(points, tolerance) {
        // Ramer-Douglas-Peucker algorithm
        if (points.length <= 2) return points;
        const first = points[0];
        const last = points[points.length - 1];
        let maxDist = 0;
        let maxIdx = 0;
        for (let i = 1; i < points.length - 1; i++) {
            const d = this._perpendicularDist(points[i], first, last);
            if (d > maxDist) {
                maxDist = d;
                maxIdx = i;
            }
        }
        if (maxDist > tolerance) {
            const left = this._simplifyPoints(points.slice(0, maxIdx + 1), tolerance);
            const right = this._simplifyPoints(points.slice(maxIdx), tolerance);
            return left.slice(0, -1).concat(right);
        }
        return [first, last];
    }

    _perpendicularDist(pt, lineStart, lineEnd) {
        const dx = lineEnd[0] - lineStart[0];
        const dy = lineEnd[1] - lineStart[1];
        const lenSq = dx * dx + dy * dy;
        if (lenSq === 0) {
            const ex = pt[0] - lineStart[0];
            const ey = pt[1] - lineStart[1];
            return Math.sqrt(ex * ex + ey * ey);
        }
        const t = ((pt[0] - lineStart[0]) * dx + (pt[1] - lineStart[1]) * dy) / lenSq;
        const cx = lineStart[0] + t * dx;
        const cy = lineStart[1] + t * dy;
        const ex = pt[0] - cx;
        const ey = pt[1] - cy;
        return Math.sqrt(ex * ex + ey * ey);
    }

    onUndoDrawing() {
        if (this._undoStack.length === 0) return;
        this._undoStack.pop();
        const updated = [...this.state.pendingDrawings];
        updated.pop();
        this.state.pendingDrawings = updated;
    }

    onCancelAnnotation() {
        this.state.pendingPin = null;
        this.state.pinMode = false;
        this.state.pendingDrawings = [];
        this.state.activeShape = null;
        this._undoStack = [];
    }

    // ─── SVG Shape Data for Template ────────────────────
    // Convert shape points array to SVG points string
    _pointsToStr(points) {
        if (!points || points.length < 2) return "";
        return points.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
    }

    // Arrow marker ID from color
    _arrowMarkerId(color) {
        return "arrow-" + color.replace("#", "");
    }

    _arrowMarkerUrl(color) {
        return "url(#" + this._arrowMarkerId(color) + ")";
    }

    // Flatten saved annotation drawings — only show for the selected/highlighted comment
    get savedDrawingShapes() {
        const sel = this.state.highlightedAnnotation;
        if (sel === null) return []; // No comment selected → no drawings visible
        const result = [];
        for (const ann of this.state.annotations) {
            if (ann.id !== sel) continue; // Only the selected comment's drawings
            if (!ann.drawing_data || ann.drawing_data.length === 0) continue;
            for (let i = 0; i < ann.drawing_data.length; i++) {
                const s = ann.drawing_data[i];
                result.push({
                    ...s,
                    key: "saved-" + ann.id + "-" + i,
                    annId: ann.id,
                    pointsStr: s.type === "freehand" ? this._pointsToStr(s.points) : "",
                    markerEnd: s.type === "arrow" ? this._arrowMarkerUrl(s.color) : "",
                    isHighlighted: true,
                });
            }
        }
        return result;
    }

    // Pending drawings for current editor session
    get pendingDrawingShapes() {
        return this.state.pendingDrawings.map((s, i) => ({
            ...s,
            key: "pending-" + i,
            pointsStr: s.type === "freehand" ? this._pointsToStr(s.points) : "",
            markerEnd: s.type === "arrow" ? this._arrowMarkerUrl(s.color) : "",
        }));
    }

    // Active shape being drawn right now
    get activeShapeData() {
        const s = this.state.activeShape;
        if (!s) return null;
        return {
            ...s,
            pointsStr: s.type === "freehand" ? this._pointsToStr(s.points) : "",
            markerEnd: s.type === "arrow" ? this._arrowMarkerUrl(s.color) : "",
        };
    }

    // Whether annotation editor is active (pin placed or drawings started)
    get isEditorActive() {
        return !!this.state.pendingPin || this.state.pendingDrawings.length > 0;
    }

    // ─── Hover Cursor ───────────────────────────────────
    onCanvasMouseMove(ev) {
        if (this.state.drawingTool || this.state.pinMode || this.state.isDrawing) {
            this.state.hoverCursorVisible = false;
            return;
        }
        if (!this.isImage) return;
        // Use container rect — hover cursor is positioned relative to container
        const container = this.imageContainerRef.el;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        this.state.hoverCursorX = ((ev.clientX - rect.left) / rect.width) * 100;
        this.state.hoverCursorY = ((ev.clientY - rect.top) / rect.height) * 100;
        this.state.hoverCursorVisible = true;
    }

    onCanvasMouseLeave() {
        this.state.hoverCursorVisible = false;
    }

    // ─── Global Keyboard ────────────────────────────────
    _onGlobalKeydown(ev) {
        if (ev.key === "Escape") {
            if (this.state.isDrawing) {
                this.state.isDrawing = false;
                this.state.activeShape = null;
                this._drawStartPoint = null;
            } else if (this.state.drawingTool) {
                this.state.drawingTool = null;
            } else if (this.state.colorPickerOpen) {
                this.state.colorPickerOpen = false;
            } else if (this.state.zoomDropdownOpen) {
                this.state.zoomDropdownOpen = false;
            }
        }
    }

    // ─── Voice Recording ────────────────────────────────
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = MediaRecorder.isTypeSupported("audio/webm")
                ? "audio/webm" : "audio/mp4";
            this._mediaRecorder = new MediaRecorder(stream, { mimeType });
            this._audioChunks = [];

            this._mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) this._audioChunks.push(e.data);
            };

            this._mediaRecorder.onstop = () => {
                this._audioBlob = new Blob(this._audioChunks, { type: mimeType });
                this._audioUrl = URL.createObjectURL(this._audioBlob);
                this.state.hasVoiceMessage = true;
                stream.getTracks().forEach(t => t.stop());
            };

            this._mediaRecorder.start();
            this.state.isRecording = true;
            this.state.recordingDuration = 0;
            this._recordingTimer = setInterval(() => {
                this.state.recordingDuration++;
            }, 1000);
        } catch (e) {
            this.notification.add(this._tr('micDenied', "Microphone access denied"), { type: "danger" });
        }
    }

    stopRecording() {
        if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
            this._mediaRecorder.stop();
        }
        this.state.isRecording = false;
        if (this._recordingTimer) {
            clearInterval(this._recordingTimer);
            this._recordingTimer = null;
        }
    }

    deleteVoiceMessage() {
        this._clearVoiceRecording();
    }

    _clearVoiceRecording() {
        if (this._audioUrl) {
            URL.revokeObjectURL(this._audioUrl);
        }
        this._audioBlob = null;
        this._audioUrl = null;
        this._audioChunks = [];
        this.state.hasVoiceMessage = false;
        this.state.isRecording = false;
        this.state.recordingDuration = 0;
        if (this._recordingTimer) {
            clearInterval(this._recordingTimer);
            this._recordingTimer = null;
        }
    }

    getVoiceUrl() {
        return this._audioUrl || "";
    }

    formatRecordingDuration() {
        const m = Math.floor(this.state.recordingDuration / 60);
        const s = this.state.recordingDuration % 60;
        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }

    // ─── File Attachments ───────────────────────────────
    onAttachFile() {
        const input = this.fileInputRef.el;
        if (input) input.click();
    }

    onFileSelected(ev) {
        const files = Array.from(ev.target.files || []);
        const updated = [...this.state.pendingAttachments, ...files];
        this.state.pendingAttachments = updated;
        ev.target.value = "";
    }

    removeAttachment(index) {
        const updated = [...this.state.pendingAttachments];
        updated.splice(index, 1);
        this.state.pendingAttachments = updated;
    }

    _fileToBase64(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(",")[1]);
            reader.readAsDataURL(file);
        });
    }

    _blobToBase64(blob) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(",")[1]);
            reader.readAsDataURL(blob);
        });
    }

    async _uploadAttachments(model, recordId, files) {
        for (const file of files) {
            const data = await this._fileToBase64(file);
            await this.orm.call(model, "add_attachment", [recordId], {
                name: file.name,
                data: data,
                mimetype: file.type || "application/octet-stream",
            });
        }
    }

    // ─── @Mention Detection ─────────────────────────────
    onCommentInput(ev) {
        this.state.newComment = ev.target.value;
        this._detectMention(ev.target);
    }

    onCommentKeydown(ev) {
        if (this.state.mentionActive && this.mentionSuggestions.length > 0) {
            if (ev.key === "ArrowDown") {
                ev.preventDefault();
                this.state.mentionIndex = (this.state.mentionIndex + 1) % this.mentionSuggestions.length;
                return;
            }
            if (ev.key === "ArrowUp") {
                ev.preventDefault();
                this.state.mentionIndex = (this.state.mentionIndex - 1 + this.mentionSuggestions.length) % this.mentionSuggestions.length;
                return;
            }
            if (ev.key === "Enter") {
                ev.preventDefault();
                this.onMentionSelect(this.mentionSuggestions[this.state.mentionIndex]);
                return;
            }
            if (ev.key === "Escape") {
                ev.preventDefault();
                this.state.mentionActive = false;
                return;
            }
        }
    }

    _detectMention(textarea) {
        const val = textarea.value;
        const cursor = textarea.selectionStart;
        let atPos = -1;
        for (let i = cursor - 1; i >= 0; i--) {
            if (val[i] === "@") { atPos = i; break; }
            if (val[i] === " " || val[i] === "\n") break;
        }
        if (atPos >= 0) {
            const query = val.substring(atPos + 1, cursor);
            this.state.mentionActive = true;
            this.state.mentionQuery = query;
            this.state.mentionIndex = 0;
        } else {
            this.state.mentionActive = false;
        }
    }

    onMentionSelect(user) {
        const textarea = this.commentRef.el;
        if (!textarea) return;

        const val = textarea.value;
        const cursor = textarea.selectionStart;
        let atPos = -1;
        for (let i = cursor - 1; i >= 0; i--) {
            if (val[i] === "@") { atPos = i; break; }
            if (val[i] === " " || val[i] === "\n") break;
        }
        if (atPos < 0) return;

        const before = val.substring(0, atPos);
        const after = val.substring(cursor);
        const insertion = "@" + user.name + " ";
        this.state.newComment = before + insertion + after;
        this.state.mentionActive = false;

        if (!this._pendingMentions.find(m => m.id === user.id)) {
            this._pendingMentions.push(user);
        }

        const newPos = before.length + insertion.length;
        setTimeout(() => {
            textarea.focus();
            textarea.setSelectionRange(newPos, newPos);
        }, 10);
    }

    _processBodyWithMentions(text) {
        let body = text;
        const mentionIds = [];
        for (const user of this._pendingMentions) {
            const pattern = "@" + user.name;
            if (body.includes(pattern)) {
                body = body.replace(
                    pattern,
                    '<span class="proofing-mention">@' + user.name + '</span>'
                );
                mentionIds.push(user.id);
            }
        }
        return { body, mentionIds };
    }

    // ─── Add Comment ────────────────────────────────────
    async onAddComment() {
        const hasText = this.state.newComment.trim().length > 0;
        const hasVoice = this.state.hasVoiceMessage;
        const hasFiles = this.state.pendingAttachments.length > 0;
        const hasDrawings = this.state.pendingDrawings.length > 0;
        if (!hasText && !hasVoice && !hasFiles && !hasDrawings) return;

        const { body, mentionIds } = this._processBodyWithMentions(
            this.state.newComment || ""
        );

        const vals = {
            version_id: this.state.currentVersion.id,
            body: body || (hasDrawings ? "(drawing annotation)" : "(voice message)"),
            step_id: this.stepId || false,
            visibility: this.state.commentVisibility,
        };

        if (mentionIds.length > 0) {
            vals.mentioned_user_ids = [[6, 0, mentionIds]];
        }

        // Drawing data
        if (hasDrawings) {
            vals.drawing_data = JSON.stringify(this.state.pendingDrawings);
        }

        if (this.state.pendingPin) {
            vals.annotation_type = "point";
            vals.x_percent = this.state.pendingPin.x_percent;
            vals.y_percent = this.state.pendingPin.y_percent;
        } else if (this.isVideo && this.videoRef.el) {
            vals.annotation_type = "timestamp";
            vals.timestamp_seconds = this.videoRef.el.currentTime;
        } else {
            vals.annotation_type = "general";
        }

        const [newId] = await this.orm.create("proofing.annotation", [vals]);

        // Upload voice message
        if (hasVoice && this._audioBlob) {
            const voiceData = await this._blobToBase64(this._audioBlob);
            const ext = this._audioBlob.type.includes("webm") ? "webm" : "m4a";
            await this.orm.call("proofing.annotation", "add_attachment", [newId], {
                name: "voice_message." + ext,
                data: voiceData,
                mimetype: this._audioBlob.type,
            });
        }

        // Upload file attachments
        if (hasFiles) {
            await this._uploadAttachments(
                "proofing.annotation", newId, this.state.pendingAttachments
            );
        }

        // Reset
        this.state.newComment = "";
        this.state.pendingPin = null;
        this.state.pinMode = false;
        this.state.pendingAttachments = [];
        this._pendingMentions = [];
        this._clearVoiceRecording();
        this._resetDrawingState();
        await this.loadData();
    }

    // ─── Pin marker click → highlight comment ───────────
    onMarkerClick(ann) {
        this.state.highlightedAnnotation = ann.id;
        this.state.expandedAnnotations[ann.id] = true;
        setTimeout(() => {
            const el = document.getElementById("ann-" + ann.id);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 50);
    }

    onAnnotationClick(ann) {
        this.state.highlightedAnnotation =
            this.state.highlightedAnnotation === ann.id ? null : ann.id;
    }

    onAnnotationHover(ann) {
        // Only highlight on hover if no comment is currently selected (clicked)
        if (this.state.highlightedAnnotation === null) {
            this._hoverAnnotation = ann.id;
        }
    }

    onAnnotationLeave() {
        this._hoverAnnotation = null;
    }

    // ─── Video seek ─────────────────────────────────────
    seekToTimestamp(seconds) {
        const vid = this.videoRef.el;
        if (vid) {
            vid.currentTime = seconds;
            vid.play();
        }
    }

    onTimelineMarkerClick(ann) {
        this.seekToTimestamp(ann.timestamp_seconds);
        this.onMarkerClick(ann);
    }

    getTimelinePosition(seconds) {
        if (!this.state.videoDuration) return "0%";
        return ((seconds / this.state.videoDuration) * 100) + "%";
    }

    // ─── Reply threads ──────────────────────────────────
    toggleReplies(ann) {
        const expanded = { ...this.state.expandedAnnotations };
        expanded[ann.id] = !expanded[ann.id];
        this.state.expandedAnnotations = expanded;
    }

    isExpanded(ann) {
        return !!this.state.expandedAnnotations[ann.id];
    }

    getReplyText(ann) {
        return this.state.replyTexts[ann.id] || "";
    }

    setReplyText(ann, ev) {
        const texts = { ...this.state.replyTexts };
        texts[ann.id] = ev.target.value;
        this.state.replyTexts = texts;
    }

    onReplyKeydown(ann, ev) {
        if (ev.key === "Enter") {
            this.onAddReply(ann);
        }
    }

    async onAddReply(ann) {
        const text = (this.state.replyTexts[ann.id] || "").trim();
        if (!text) return;
        await this.orm.create("proofing.annotation.reply", [{
            annotation_id: ann.id,
            body: text,
        }]);
        const texts = { ...this.state.replyTexts };
        texts[ann.id] = "";
        this.state.replyTexts = texts;
        await this.loadData();
        this.state.expandedAnnotations[ann.id] = true;
    }

    // ─── Resolve / Reopen ───────────────────────────────
    async onResolve(ann) {
        await this.orm.call("proofing.annotation", "action_resolve", [ann.id]);
        await this.loadData();
    }

    async onReopen(ann) {
        await this.orm.call("proofing.annotation", "action_reopen", [ann.id]);
        await this.loadData();
    }

    toggleShowResolved() {
        this.state.showResolved = !this.state.showResolved;
    }

    // ─── Formatting helpers ─────────────────────────────
    formatTimestamp(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        if (diff < 60000) return "just now";
        if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
        if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
        return d.toLocaleDateString();
    }

    formatFileSize(bytes) {
        if (!bytes) return "";
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / 1048576).toFixed(1) + " MB";
    }

    onBackToDashboard() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "proofing_project_dashboard",
            name: this.state.project?.name || "Project",
            params: { project_id: this.projectId },
        }, { clearBreadcrumbs: true });
    }

    getFileIcon(fileType) {
        switch (fileType) {
            case "video": return "fa-film";
            case "image": return "fa-image";
            case "pdf": return "fa-file-pdf-o";
            case "audio": return "fa-music";
            default: return "fa-file-o";
        }
    }

    getAttachmentIcon(mimetype) {
        if (!mimetype) return "fa-file-o";
        if (mimetype.startsWith("image/")) return "fa-file-image-o";
        if (mimetype === "application/pdf") return "fa-file-pdf-o";
        if (mimetype.startsWith("video/")) return "fa-file-video-o";
        return "fa-file-o";
    }

    getDecisionColor(decision) {
        switch (decision) {
            case "approved": return "text-success";
            case "changes_requested": return "text-warning";
            default: return "text-muted";
        }
    }
}

registry.category("actions").add("proofing_review_page", ProofingReviewPage);
