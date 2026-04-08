/** @odoo-module **/
import { Component, useState, useRef, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class ProofingDashboard extends Component {
    static template = "creative_studio.ProjectDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.fileInputRef = useRef("uploadFileInput");

        this.state = useState({
            project: null,
            steps: [],
            files: [],
            fileCount: 0,
            loading: true,
            expandedFiles: {},
            showInfoFile: null,
            sortBy: "newest",
            showSortMenu: false,
            // Upload dialog
            showUploadDialog: false,
            pendingFiles: [],
            isDragOver: false,
            uploading: false,
        });

        this.projectId = this.props.action?.params?.project_id
            || this.props.action?.context?.active_id;

        onWillStart(async () => {
            if (this.projectId) {
                await this.loadData();
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "proofing.project", "get_dashboard_data", [this.projectId]
            );
            this.state.project = data.project;
            this.state.steps = data.steps;
            this.state.files = data.files;
            this.state.fileCount = data.file_count;
            this._serverTranslations = data.translations || {};
        } catch (e) {
            this.notification.add(_t("Failed to load project data"), { type: "danger" });
        }
        this.state.loading = false;
    }

    // ─── Translated strings for OWL template ────────
    // Server-side translations via Python _() as primary source,
    // JS _t() as fallback for strings not yet loaded from server.
    get T() {
        const s = this._serverTranslations || {};
        return {
            uploadFile: s.uploadFile || _t("Upload file"),
            sortFiles: s.sortFiles || _t("Sort files"),
            sortBy: s.sortBy || _t("SORT BY"),
            newestFile: s.newestFile || _t("Newest file"),
            fileName: s.fileName || _t("File name"),
            allFiles: s.allFiles || _t("All files"),
            noReviewers: s.noReviewers || _t("No reviewers"),
            noFilesYet: s.noFilesYet || _t("No files yet"),
            clickUpload: s.clickUpload || _t('Click "Upload file" to get started'),
            startReview: s.startReview || _t("Start review"),
            manageReviewers: s.manageReviewers || _t("Manage reviewers"),
            deleteThisReview: s.deleteThisReview || _t("Delete this review"),
            inviteReviewers: s.inviteReviewers || _t("Invite reviewers"),
            uploadNewVersion: s.uploadNewVersion || _t("Upload a new version"),
            moreInfo: s.moreInfo || _t("More information"),
            downloadVersion: s.downloadVersion || _t("Download version"),
            deleteVersion: s.deleteVersion || _t("Delete version"),
            deleteAllVersions: s.deleteAllVersions || _t("Delete all versions"),
            openReview: s.openReview || _t("Open review"),
            downloadThisVersion: s.downloadThisVersion || _t("Download this version"),
            reviewNotStarted: s.reviewNotStarted || _t("Review not started"),
            fileInfo: s.fileInfo || _t("File Information"),
            version: s.version || _t("Version:"),
            originalFileName: s.originalFileName || _t("Original file name:"),
            fileType: s.fileType || _t("File type:"),
            uploadedBy: s.uploadedBy || _t("Uploaded by:"),
            uploadedOn: s.uploadedOn || _t("Uploaded on:"),
            projectSettings: s.projectSettings || _t("Project settings"),
            browseOrDrop: s.browseOrDrop || _t("Browse or drop your files here"),
            filesAdded: s.filesAdded || _t("files added"),
            uploadAndStart: s.uploadAndStart || _t("Upload and start review"),
            cancel: s.cancel || _t("Cancel"),
            campaign: s.campaign || _t("Campaign"),
            viewCampaign: s.viewCampaign || _t("View Campaign"),
            noCampaign: s.noCampaign || _t("No campaign linked"),
        };
    }

    get sortedFiles() {
        const files = [...this.state.files];
        if (this.state.sortBy === "name") {
            files.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
        } else {
            // newest first (default) — by id desc as proxy for creation order
            files.sort((a, b) => b.id - a.id);
        }
        return files;
    }

    toggleSortMenu() {
        this.state.showSortMenu = !this.state.showSortMenu;
    }

    setSortBy(value) {
        this.state.sortBy = value;
        this.state.showSortMenu = false;
    }

    toggleVersions(fileId) {
        this.state.expandedFiles[fileId] = !this.state.expandedFiles[fileId];
    }

    isExpanded(fileId) {
        return this.state.expandedFiles[fileId] || false;
    }

    getFileReview(file, stepId) {
        return file.reviews[stepId] || { state: "not_started", decision_summary: "0/0" };
    }


    onAddReviewer(step) {
        // Open a dialog to add reviewers to this step
        this.action.doAction({
            type: "ir.actions.act_window",
            name: step.name + " - Reviewers",
            res_model: "proofing.review.step",
            res_id: step.id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        }, {
            onClose: async () => {
                await this.loadData();
            },
        });
    }

    getStateColor(state) {
        switch (state) {
            case "approved": return "#28a745";
            case "in_review": return "#17a2b8";
            case "changes_requested": return "#fd7e14";
            default: return "#6c757d";
        }
    }

    getStateLabel(state) {
        const s = this._serverTranslations || {};
        switch (state) {
            case "approved": return s.approved || _t("Approved");
            case "in_review": return s.inReview || _t("In review");
            case "changes_requested": return s.changesRequested || _t("Changes requested");
            default: return s.reviewNotStarted || _t("Review not started");
        }
    }

    getFileIcon(fileType) {
        switch (fileType) {
            case "video": return "fa-film";
            case "image": return "fa-image";
            case "pdf": return "fa-file-pdf-o";
            case "audio": return "fa-music";
            case "document": return "fa-file-text-o";
            default: return "fa-file-o";
        }
    }

    async onStartReview(file, step) {
        const review = this.getFileReview(file, step.id);
        if (review.id && review.state === "not_started") {
            await this.orm.call("proofing.file.review", "action_start_review", [review.id]);
            this.notification.add(
                _t("Review started for '%s' in '%s'", file.name, step.name),
                { type: "info" }
            );
            await this.loadData();
        }
    }

    onCellClick(file, step) {
        const review = this.getFileReview(file, step.id);
        if (review.state !== "not_started") {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "proofing_review_page",
                name: file.name,
                params: {
                    project_id: this.projectId,
                    file_id: file.id,
                    step_id: step.id,
                },
            });
        }
    }

    async onDeleteStep(step) {
        if (confirm(_t("Delete review step '%s'? All review decisions in this step will be lost.", step.name))) {
            await this.orm.unlink("proofing.review.step", [step.id]);
            await this.loadData();
        }
    }

    async onDeleteFileReview(file, step) {
        if (confirm(_t("Delete the review for '%s' in step '%s'? The review will be reset and all comments will be cleared.", file.name, step.name))) {
            const review = this.getFileReview(file, step.id);
            if (review.id) {
                await this.orm.call("proofing.file.review", "action_reset_review", [review.id]);
            }
            await this.loadData();
        }
    }

    // ─── Upload Dialog ────────────────────────────────
    onUploadFile() {
        this.state.showUploadDialog = true;
        this.state.pendingFiles = [];
        this.state.isDragOver = false;
        this.state.uploading = false;
    }

    onCloseUploadDialog() {
        this.state.showUploadDialog = false;
        this.state.pendingFiles = [];
    }

    onBrowseFiles() {
        const input = this.fileInputRef.el;
        if (input) input.click();
    }

    onFilesSelected(ev) {
        const files = Array.from(ev.target.files || []);
        this._addFiles(files);
        ev.target.value = "";
    }

    onDropZoneDragOver(ev) {
        ev.preventDefault();
        this.state.isDragOver = true;
    }

    onDropZoneDragLeave(ev) {
        ev.preventDefault();
        this.state.isDragOver = false;
    }

    onDropZoneDrop(ev) {
        ev.preventDefault();
        this.state.isDragOver = false;
        const files = Array.from(ev.dataTransfer.files || []);
        this._addFiles(files);
    }

    _addFiles(files) {
        const updated = [...this.state.pendingFiles, ...files];
        this.state.pendingFiles = updated;
    }

    onRemovePendingFile(index) {
        const updated = [...this.state.pendingFiles];
        updated.splice(index, 1);
        this.state.pendingFiles = updated;
    }

    _fileToBase64(file) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(",")[1]);
            reader.readAsDataURL(file);
        });
    }

    async onUploadAndStart() {
        if (this.state.pendingFiles.length === 0) return;
        this.state.uploading = true;
        try {
            const fileList = [];
            for (const file of this.state.pendingFiles) {
                const data = await this._fileToBase64(file);
                fileList.push({
                    name: file.name,
                    data: data,
                    mimetype: file.type || "application/octet-stream",
                });
            }
            await this.orm.call(
                "proofing.project", "upload_files",
                [[this.projectId], fileList]
            );
            this.notification.add(
                _t("%s file(s) uploaded successfully", fileList.length),
                { type: "success" }
            );
            this.state.showUploadDialog = false;
            this.state.pendingFiles = [];
            await this.loadData();
        } catch (e) {
            this.notification.add(_t("Upload failed"), { type: "danger" });
        }
        this.state.uploading = false;
    }

    async onFileClick(file) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "proofing_review_page",
            name: file.name,
            params: {
                project_id: this.projectId,
                file_id: file.id,
            },
        });
    }

    onVersionStepClick(file, version, step) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "proofing_review_page",
            name: file.name + " v" + version.number,
            params: {
                project_id: this.projectId,
                file_id: version.file_id || file.id,
                step_id: step.id,
                version_id: version.id,
            },
        });
    }

    async onUploadNewVersion(file) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Upload New Version"),
            res_model: "proofing.upload.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_project_id: this.projectId,
                default_file_id: file.id,
            },
        }, {
            onClose: async () => {
                await this.loadData();
            },
        });
    }

    onShowInfo(file) {
        this.state.showInfoFile = file;
    }

    onCloseInfo() {
        this.state.showInfoFile = null;
    }

    async onDeleteVersion(file) {
        if (confirm(_t("Delete version %s of '%s'?", file.version, file.name))) {
            await this.orm.call("proofing.file", "action_delete_current_version", [file.id]);
            await this.loadData();
        }
    }

    async onDeleteAllVersions(file) {
        if (confirm(_t("Delete '%s' and all its versions? This action cannot be undone.", file.name))) {
            await this.orm.call("proofing.file", "action_delete_all_versions", [file.id]);
            await this.loadData();
        }
    }

    onShowVersionInfo(version) {
        this.state.showInfoFile = {
            version: version.number,
            original_filename: version.filename,
            mimetype: version.mimetype,
            uploaded_by: version.uploaded_by,
            upload_date: version.upload_date,
        };
    }

    async onDeleteSpecificVersion(version) {
        if (confirm(_t("Delete version %s?", version.number))) {
            await this.orm.unlink("proofing.version", [version.id]);
            await this.loadData();
        }
    }

    onCampaignClick() {
        if (this.state.project && this.state.project.campaign_id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "utm.campaign",
                res_id: this.state.project.campaign_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    onBackToProjects() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Projects"),
            res_model: "proofing.project",
            view_mode: "kanban,list,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }
}

registry.category("actions").add("proofing_project_dashboard", ProofingDashboard);
