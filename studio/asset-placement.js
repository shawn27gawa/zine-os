(() => {
    "use strict";

    const decodePayload = (elementId) => {
        const encoded = document.getElementById(elementId).textContent.trim();
        const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
        return new TextDecoder().decode(bytes);
    };

    const config = JSON.parse(decodePayload("studio-config"));
    const previewSource = decodePayload("preview-source");
    const previewFrame = document.getElementById("preview-frame");
    const previewFrameWrap = document.getElementById("preview-frame-wrap");
    const message = document.getElementById("studio-message");
    const selectionLabel = document.getElementById("selection-label");
    const selectionFile = document.getElementById("selection-file");
    const controls = document.getElementById("placement-controls");
    const textControls = document.getElementById("text-controls");
    const freeLayerControls = document.getElementById("free-layer-controls");
    const slotRegistry = new Map();
    const textRegistry = new Map();
    const placementState = new Map();
    const textState = new Map();

    let selectedKey = null;
    let selectedKind = null;
    let activeMode = "desktop";
    let manifestObjectUrl = null;

    const controlElements = {
        fit: document.getElementById("placement-fit"),
        x: document.getElementById("placement-x"),
        y: document.getElementById("placement-y"),
        scale: document.getElementById("placement-scale"),
        frameX: document.getElementById("frame-x"),
        frameY: document.getElementById("frame-y"),
        frameSize: document.getElementById("frame-size"),
    };

    const outputElements = {
        x: document.getElementById("placement-x-output"),
        y: document.getElementById("placement-y-output"),
        scale: document.getElementById("placement-scale-output"),
        frameX: document.getElementById("frame-x-output"),
        frameY: document.getElementById("frame-y-output"),
        frameSize: document.getElementById("frame-size-output"),
    };

    const textControlElements = {
        font_size_px: document.getElementById("text-font-size"),
        line_height: document.getElementById("text-line-height"),
        width_percent: document.getElementById("text-width"),
        x_mm: document.getElementById("text-x"),
        y_mm: document.getElementById("text-y"),
        columns: document.getElementById("text-columns"),
    };

    const textOutputElements = {
        font_size_px: document.getElementById("text-font-size-output"),
        line_height: document.getElementById("text-line-height-output"),
        width_percent: document.getElementById("text-width-output"),
        x_mm: document.getElementById("text-x-output"),
        y_mm: document.getElementById("text-y-output"),
        columns: document.getElementById("text-columns-output"),
    };

    const positionValue = (value, axis) => {
        const keywordValues = axis === "x"
            ? {left: 0, center: 50, right: 100}
            : {top: 0, center: 50, bottom: 100};

        if (value in keywordValues) return keywordValues[value];
        if (value?.endsWith("%")) return Number.parseFloat(value);
        return 50;
    };

    const defaultPosition = (slot) => {
        const values = String(slot.defaultPosition || "center center")
            .trim()
            .toLowerCase()
            .split(/\s+/);
        return {
            x: positionValue(values[0], "x"),
            y: positionValue(values[1] || "center", "y"),
        };
    };

    const defaultPlacement = (slot) => ({
        fit: slot.defaultFit || "cover",
        ...defaultPosition(slot),
        scale: 1,
        frameX: slot.frame?.x ?? 50,
        frameY: slot.frame?.y ?? 50,
        frameSize: slot.frame?.size ?? 35,
    });

    const getModeKey = () => activeMode === "mobile" ? "mobile" : "desktop";

    const ensureState = (slot) => {
        if (!placementState.has(slot.key)) {
            const desktop = defaultPlacement(slot);
            placementState.set(slot.key, {
                key: slot.key,
                pageUnitId: slot.pageUnitId,
                pages: slot.pages,
                kind: slot.kind,
                blockId: slot.blockId || null,
                assetId: slot.assetId || null,
                assetIndex: slot.assetIndex ?? null,
                cellIndex: slot.cellIndex ?? null,
                role: slot.role || null,
                monochrome: Boolean(slot.monochrome),
                source: null,
                previewDataUrl: null,
                dirty: false,
                settings: {
                    desktop,
                    mobile: {...desktop},
                },
            });
        }

        return placementState.get(slot.key);
    };

    const computedTypography = (element) => {
        const computed = element.ownerDocument.defaultView.getComputedStyle(element);
        const fontSize = Number.parseFloat(computed.fontSize) || 16;
        const lineHeightPixels = Number.parseFloat(computed.lineHeight);
        return {
            font_size_px: fontSize,
            line_height: Number.isFinite(lineHeightPixels)
                ? lineHeightPixels / fontSize
                : 1.5,
            width_percent: 100,
            x_mm: 0,
            y_mm: 0,
            columns: Number.parseInt(computed.columnCount, 10) || 1,
            rule_spacing_mm: null,
        };
    };

    const ensureTextState = (slot, element) => {
        if (!textState.has(slot.key)) {
            textState.set(slot.key, {
                key: slot.key,
                pageUnitId: slot.pageUnitId,
                blockId: slot.blockId,
                field: slot.field,
                originalText: slot.originalText,
                text: slot.originalText,
                typography: slot.typography || null,
                initialTypography: slot.typography || null,
                defaultTypography: computedTypography(element),
                dirty: false,
            });
        }
        return textState.get(slot.key);
    };

    const currentSettings = (slot) => {
        const state = ensureState(slot);
        return state.settings[getModeKey()];
    };

    const updateOutputs = (settings) => {
        outputElements.x.value = `${Math.round(settings.x)}%`;
        outputElements.y.value = `${Math.round(settings.y)}%`;
        outputElements.scale.value = `${Number(settings.scale).toFixed(2)}×`;
        outputElements.frameX.value = `${Math.round(settings.frameX)}%`;
        outputElements.frameY.value = `${Math.round(settings.frameY)}%`;
        outputElements.frameSize.value = `${Math.round(settings.frameSize)}%`;
    };

    const imageForSlot = (registered) => registered.element.querySelector("img");

    const applyPlacement = (registered) => {
        const slot = registered.slot;
        const settings = currentSettings(slot);
        const image = imageForSlot(registered);

        if (image) {
            image.style.objectFit = settings.fit;
            image.style.objectPosition = `${settings.x}% ${settings.y}%`;
            image.style.transformOrigin = `${settings.x}% ${settings.y}%`;
            image.style.transform = `scale(${settings.scale})`;
        }

        if (slot.kind === "free-layer") {
            registered.element.style.left = `${settings.frameX}%`;
            registered.element.style.top = `${settings.frameY}%`;
            registered.element.style.width = `${settings.frameSize}%`;
        }
    };

    const refreshInspector = () => {
        controls.hidden = true;
        textControls.hidden = true;

        if (!selectedKey) {
            selectionLabel.textContent = "Select an image or text slot.";
            return;
        }

        if (selectedKind === "text" && textRegistry.has(selectedKey)) {
            const registered = textRegistry.get(selectedKey);
            const state = ensureTextState(registered.slot, registered.element);
            const typography = state.typography || state.defaultTypography;
            textControls.hidden = false;
            selectionLabel.textContent = registered.slot.label;
            document.getElementById("text-content").value = state.text;
            Object.entries(textControlElements).forEach(([property, element]) => {
                element.value = typography[property];
            });
            textOutputElements.font_size_px.value = `${Number(typography.font_size_px).toFixed(2)}px`;
            textOutputElements.line_height.value = Number(typography.line_height).toFixed(2);
            textOutputElements.width_percent.value = `${Math.round(typography.width_percent)}%`;
            textOutputElements.x_mm.value = `${Number(typography.x_mm).toFixed(1)}mm`;
            textOutputElements.y_mm.value = `${Number(typography.y_mm).toFixed(1)}mm`;
            textOutputElements.columns.value = String(typography.columns);
            return;
        }

        if (!slotRegistry.has(selectedKey)) {
            controls.hidden = true;
            selectionLabel.textContent = "Select an image or text slot.";
            return;
        }

        const registered = slotRegistry.get(selectedKey);
        const state = ensureState(registered.slot);
        const settings = currentSettings(registered.slot);

        controls.hidden = false;
        freeLayerControls.hidden = registered.slot.kind !== "free-layer";
        selectionLabel.textContent = registered.slot.label;
        selectionFile.textContent = state.source?.name || registered.slot.assetId || "Not assigned";

        controlElements.fit.value = settings.fit;
        controlElements.x.value = settings.x;
        controlElements.y.value = settings.y;
        controlElements.scale.value = settings.scale;
        controlElements.frameX.value = settings.frameX;
        controlElements.frameY.value = settings.frameY;
        controlElements.frameSize.value = settings.frameSize;
        updateOutputs(settings);
    };

    const selectSlot = (key) => {
        if (selectedKey && slotRegistry.has(selectedKey)) {
            slotRegistry.get(selectedKey).element.classList.remove("studio-selected-slot");
        }
        if (selectedKey && textRegistry.has(selectedKey)) {
            textRegistry.get(selectedKey).element.classList.remove("studio-selected-text");
        }

        selectedKey = key;
        selectedKind = "asset";
        const registered = slotRegistry.get(key);
        registered.element.classList.add("studio-selected-slot");
        refreshInspector();
    };

    const selectTextSlot = (key) => {
        if (selectedKey && slotRegistry.has(selectedKey)) {
            slotRegistry.get(selectedKey).element.classList.remove("studio-selected-slot");
        }
        if (selectedKey && textRegistry.has(selectedKey)) {
            textRegistry.get(selectedKey).element.classList.remove("studio-selected-text");
        }
        selectedKey = key;
        selectedKind = "text";
        const registered = textRegistry.get(key);
        registered.element.classList.add("studio-selected-text");
        refreshInspector();
    };

    const createThumbnail = (file) => new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => {
            const image = new Image();
            image.onload = () => {
                const maxDimension = 480;
                const ratio = Math.min(1, maxDimension / Math.max(image.width, image.height));
                const canvas = document.createElement("canvas");
                canvas.width = Math.max(1, Math.round(image.width * ratio));
                canvas.height = Math.max(1, Math.round(image.height * ratio));
                canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
                resolve(canvas.toDataURL("image/jpeg", 0.76));
            };
            image.onerror = () => resolve(null);
            image.src = reader.result;
        };
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
    });

    const installImage = (registered, source) => {
        let image = imageForSlot(registered);

        if (!image) {
            registered.element.replaceChildren();
            image = registered.element.ownerDocument.createElement("img");
            image.alt = registered.slot.label;
            registered.element.appendChild(image);
        }

        image.src = source;
        registered.element.classList.add("studio-has-image");
        applyPlacement(registered);
    };

    const assignFile = async (registered, file) => {
        if (!file.type.startsWith("image/")) {
            message.textContent = `${file.name} is not an image.`;
            return;
        }

        const state = ensureState(registered.slot);
        const objectUrl = URL.createObjectURL(file);
        installImage(registered, objectUrl);

        state.source = {
            name: file.name,
            type: file.type,
            size: file.size,
            lastModified: file.lastModified,
        };
        state.previewDataUrl = await createThumbnail(file);
        state.dirty = true;
        selectSlot(registered.slot.key);
        message.textContent = `${file.name} assigned to ${registered.slot.label}.`;
    };

    const assignMultipleToGrid = async (pageUnit, files) => {
        const gridSlots = pageUnit.slots
            .filter((slot) => slot.kind === "memory-cell")
            .map((slot) => slotRegistry.get(slot.key))
            .filter(Boolean);

        for (let index = 0; index < Math.min(files.length, gridSlots.length); index += 1) {
            await assignFile(gridSlots[index], files[index]);
        }

        message.textContent = `${Math.min(files.length, gridSlots.length)} memory-grid images assigned in filename order.`;
    };

    const registerDropSlot = (slot, element) => {
        const registered = {slot, element};
        slotRegistry.set(slot.key, registered);
        element.classList.add("studio-drop-slot");
        element.dataset.studioSlotKey = slot.key;

        if (slot.monochrome) {
            element.classList.add("studio-monochrome-slot");
        }

        element.addEventListener("click", (event) => {
            event.preventDefault();
            selectSlot(slot.key);
        });

        element.addEventListener("dragover", (event) => {
            event.preventDefault();
            element.classList.add("studio-drag-over");
        });

        element.addEventListener("dragleave", () => {
            element.classList.remove("studio-drag-over");
        });

        element.addEventListener("drop", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            element.classList.remove("studio-drag-over");
            const files = [...event.dataTransfer.files];

            if (slot.kind === "memory-cell" && files.length > 1) {
                const pageUnit = config.pageUnits[slot.articleIndex];
                await assignMultipleToGrid(pageUnit, files);
            } else if (files[0]) {
                await assignFile(registered, files[0]);
            }
        });

        return registered;
    };

    const textElementForSlot = (block, slot) => {
        if (slot.field === "content") {
            return block.querySelector(":scope > .text-content, :scope > .question, :scope > blockquote");
        }
        if (slot.field === "caption") return block.querySelector(":scope > .caption");
        if (slot.field === "title") return block.querySelector(":scope > .block-title");
        const itemMatch = slot.field.match(/^items\[(\d+)]\.text$/);
        if (itemMatch) {
            const item = block.querySelectorAll(":scope > .checklist > .checklist-item")[Number(itemMatch[1])];
            return item?.querySelector("span:last-child") || null;
        }
        return null;
    };

    const applyTextEdit = (registered) => {
        const state = ensureTextState(registered.slot, registered.element);
        registered.element.textContent = state.text;
        registered.element.style.whiteSpace = "pre-line";
        const typography = state.typography;
        if (!typography) {
            ["fontSize", "lineHeight", "width", "transform", "columnCount"].forEach((property) => {
                registered.element.style[property] = "";
            });
            return;
        }
        registered.element.style.fontSize = `${typography.font_size_px}px`;
        registered.element.style.lineHeight = String(typography.line_height);
        registered.element.style.width = `${typography.width_percent}%`;
        registered.element.style.transform = `translate(${typography.x_mm}mm, ${typography.y_mm}mm)`;
        registered.element.style.columnCount = String(typography.columns);
    };

    const registerTextSlot = (slot, element) => {
        const registered = {slot, element};
        textRegistry.set(slot.key, registered);
        element.classList.add("studio-text-slot");
        element.dataset.studioTextKey = slot.key;
        ensureTextState(slot, element);
        element.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            selectTextSlot(slot.key);
        });
        return registered;
    };

    const injectFrameStyles = (frameDocument) => {
        const style = frameDocument.createElement("style");
        style.textContent = `
            .studio-drop-slot {
                position: relative;
                overflow: hidden !important;
                cursor: pointer;
                outline: 1px dashed rgba(0, 102, 204, 0.45);
                outline-offset: -2px;
            }
            .studio-drop-slot::after {
                content: "DROP";
                position: absolute;
                right: 5px;
                bottom: 5px;
                z-index: 50;
                padding: 3px 5px;
                border-radius: 4px;
                color: #fff;
                background: rgba(0, 86, 180, 0.72);
                font: 9px/1 Inter, -apple-system, sans-serif;
                letter-spacing: 0.08em;
            }
            .studio-drop-slot.studio-has-image::after { content: "EDIT"; }
            .studio-drop-slot.studio-selected-slot {
                outline: 3px solid #0066cc;
                outline-offset: -3px;
            }
            .studio-drop-slot.studio-drag-over {
                outline: 4px solid #ff8a00;
                outline-offset: -4px;
            }
            .studio-drop-slot > img,
            .studio-drop-slot .asset > img,
            .studio-drop-slot.asset > img {
                width: 100% !important;
                height: 100% !important;
                max-width: none !important;
                display: block !important;
            }
            .studio-drop-slot figcaption,
            .studio-drop-slot .asset-type,
            .studio-drop-slot > strong,
            .studio-drop-slot > small {
                display: none !important;
            }
            .studio-monochrome-slot img {
                filter: grayscale(1) !important;
            }
            .studio-free-layer {
                position: absolute !important;
                z-index: 30;
                aspect-ratio: 0.8;
                transform: translate(-50%, -50%);
                min-height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 1px dashed rgba(0, 102, 204, 0.65);
                background: rgba(255, 255, 255, 0.74);
            }
            .studio-text-slot {
                cursor: text;
                outline: 1px dotted rgba(98, 69, 190, 0.48);
                outline-offset: 2px;
            }
            .studio-text-slot:hover {
                outline-color: rgba(98, 69, 190, 0.86);
            }
            .studio-text-slot.studio-selected-text {
                outline: 3px solid #6245be;
                outline-offset: 3px;
            }
        `;
        frameDocument.head.appendChild(style);
    };

    const initializePreview = () => {
        const frameDocument = previewFrame.contentDocument;
        injectFrameStyles(frameDocument);

        const articles = [...frameDocument.querySelectorAll(".page-unit")];

        config.pageUnits.forEach((pageUnit) => {
            const article = articles[pageUnit.articleIndex];
            if (!article) return;

            article.dataset.studioPageId = pageUnit.id;
            const pageBody = article.querySelector(".page-body");
            const blocks = [...pageBody.children].filter((child) => child.classList.contains("block"));

            pageUnit.slots.forEach((slot) => {
                slot.pageUnitId = pageUnit.id;
                slot.pages = pageUnit.pages;

                if (slot.kind === "memory-cell") {
                    const cell = pageBody.querySelectorAll(".memory-cell")[slot.cellIndex];
                    if (cell) registerDropSlot(slot, cell);
                    return;
                }

                if (slot.kind === "free-layer") {
                    const layer = frameDocument.createElement("div");
                    layer.className = "studio-free-layer asset-placeholder";
                    layer.innerHTML = `<strong>${slot.label}</strong><small>Placement preview only</small>`;
                    pageBody.appendChild(layer);
                    registerDropSlot(slot, layer);
                    applyPlacement(slotRegistry.get(slot.key));
                    return;
                }

                const block = blocks[slot.blockIndex];
                if (!block) return;

                const visuals = slot.assetIndex > 0 || block.querySelector(".gallery")
                    ? [...block.querySelectorAll(".gallery > .asset, .gallery > .asset-placeholder")]
                    : [block.querySelector(".asset, .asset-placeholder")];
                const visual = visuals[slot.assetIndex] || visuals[0];
                if (visual) registerDropSlot(slot, visual);
            });

            pageUnit.textSlots.forEach((slot) => {
                slot.pageUnitId = pageUnit.id;
                const block = blocks[slot.blockIndex];
                if (!block) return;
                const element = textElementForSlot(block, slot);
                if (element) registerTextSlot(slot, element);
            });
        });

        buildNavigation(articles);
        message.textContent = "Studio ready. Select outlined text or drop photographs onto image slots.";
    };

    const buildNavigation = (articles) => {
        const navigation = document.getElementById("page-navigation");
        navigation.replaceChildren();

        config.pageUnits.forEach((pageUnit) => {
            const button = document.createElement("button");
            const pageLabel = pageUnit.pages.length === 2
                ? `P${pageUnit.pages[0]}–${pageUnit.pages[1]}`
                : `P${pageUnit.pages[0]}`;
            const label = document.createElement("span");
            const layout = document.createElement("span");
            button.type = "button";
            label.textContent = pageLabel;
            layout.className = "studio-page-layout";
            layout.textContent = pageUnit.layoutType;
            label.appendChild(layout);
            button.appendChild(label);
            button.addEventListener("click", () => {
                navigation.querySelectorAll("button").forEach((item) => item.classList.remove("is-active"));
                button.classList.add("is-active");
                articles[pageUnit.articleIndex]?.scrollIntoView({behavior: "smooth", block: "start"});
            });
            navigation.appendChild(button);
        });
    };

    const updateSelectedSetting = (property, rawValue) => {
        if (!selectedKey || selectedKind !== "asset") return;
        const registered = slotRegistry.get(selectedKey);
        const state = ensureState(registered.slot);
        const settings = currentSettings(registered.slot);
        settings[property] = property === "fit" ? rawValue : Number(rawValue);
        state.dirty = true;
        applyPlacement(registered);
        refreshInspector();
    };

    Object.entries(controlElements).forEach(([property, element]) => {
        element.addEventListener("input", () => updateSelectedSetting(property, element.value));
        element.addEventListener("change", () => updateSelectedSetting(property, element.value));
    });

    document.getElementById("placement-reset").addEventListener("click", () => {
        if (!selectedKey || selectedKind !== "asset") return;
        const registered = slotRegistry.get(selectedKey);
        const state = ensureState(registered.slot);
        state.settings[getModeKey()] = defaultPlacement(registered.slot);
        state.dirty = true;
        applyPlacement(registered);
        refreshInspector();
    });

    document.getElementById("slot-file-input").addEventListener("change", async (event) => {
        if (!selectedKey || selectedKind !== "asset") return;
        const registered = slotRegistry.get(selectedKey);
        const files = [...event.target.files];

        if (registered.slot.kind === "memory-cell" && files.length > 1) {
            const pageUnit = config.pageUnits[registered.slot.articleIndex];
            await assignMultipleToGrid(pageUnit, files);
        } else if (files[0]) {
            await assignFile(registered, files[0]);
        }

        event.target.value = "";
    });

    document.getElementById("text-content").addEventListener("input", (event) => {
        if (!selectedKey || selectedKind !== "text") return;
        const registered = textRegistry.get(selectedKey);
        const state = ensureTextState(registered.slot, registered.element);
        state.text = event.target.value;
        state.dirty = true;
        applyTextEdit(registered);
    });

    const updateSelectedTypography = (property, rawValue) => {
        if (!selectedKey || selectedKind !== "text") return;
        const registered = textRegistry.get(selectedKey);
        const state = ensureTextState(registered.slot, registered.element);
        if (!state.typography) state.typography = {...state.defaultTypography};
        state.typography[property] = Number(rawValue);
        state.dirty = true;
        applyTextEdit(registered);
        refreshInspector();
    };

    Object.entries(textControlElements).forEach(([property, element]) => {
        element.addEventListener("input", () => updateSelectedTypography(property, element.value));
        element.addEventListener("change", () => updateSelectedTypography(property, element.value));
    });

    document.getElementById("text-reset").addEventListener("click", () => {
        if (!selectedKey || selectedKind !== "text") return;
        const registered = textRegistry.get(selectedKey);
        const state = ensureTextState(registered.slot, registered.element);
        state.text = state.originalText;
        state.typography = state.initialTypography
            ? {...state.initialTypography}
            : null;
        state.dirty = false;
        applyTextEdit(registered);
        refreshInspector();
    });

    document.querySelectorAll("[data-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            activeMode = button.dataset.mode;
            document.querySelectorAll("[data-mode]").forEach((item) => item.classList.remove("is-active"));
            button.classList.add("is-active");
            previewFrameWrap.className = `mode-${activeMode}`;
            slotRegistry.forEach((registered) => applyPlacement(registered));
            refreshInspector();
        });
    });

    const assetManifestData = () => ({
        format: "zineos-asset-placement",
        version: 1,
        projectId: config.project.id,
        zinePath: config.zinePath,
        sourceReference: config.sourceReference,
        createdAt: new Date().toISOString(),
        placements: [...placementState.values()]
            .filter((state) => state.source || state.dirty)
            .map(({dirty, ...state}) => state),
    });

    const textManifestData = () => ({
        format: "zineos-text-placement",
        version: 1,
        projectId: config.project.id,
        zinePath: config.zinePath,
        sourceReference: config.sourceReference,
        createdAt: new Date().toISOString(),
        edits: [...textState.values()]
            .filter((state) => state.dirty)
            .map(({dirty, defaultTypography, initialTypography, ...state}) => state),
    });

    const showManifest = (manifest, collectionName, filenameSuffix, title) => {
        const changes = manifest[collectionName];

        if (changes.length === 0) {
            message.textContent = `No ${title.toLowerCase()} changes to export.`;
            return;
        }

        const manifestText = JSON.stringify(manifest, null, 2);
        const handoff = document.getElementById("manifest-handoff");
        const output = document.getElementById("manifest-output");
        const download = document.getElementById("manifest-download");
        document.getElementById("manifest-title").textContent = `${title} manifest`;

        if (manifestObjectUrl) URL.revokeObjectURL(manifestObjectUrl);
        manifestObjectUrl = URL.createObjectURL(
            new Blob([manifestText], {type: "application/json"})
        );

        output.value = manifestText;
        download.href = manifestObjectUrl;
        download.download = `${config.project.id}-${filenameSuffix}.json`;
        handoff.hidden = false;
        message.textContent = `${changes.length} ${title.toLowerCase()} changes prepared for Builder review.`;
    };

    document.getElementById("asset-manifest-export").addEventListener("click", () => {
        showManifest(assetManifestData(), "placements", "asset-placement", "Asset placement");
    });

    document.getElementById("text-manifest-export").addEventListener("click", () => {
        showManifest(textManifestData(), "edits", "text-placement", "Text placement");
    });

    document.getElementById("manifest-copy").addEventListener("click", async () => {
        const output = document.getElementById("manifest-output");

        try {
            await navigator.clipboard.writeText(output.value);
            message.textContent = "Manifest JSON copied to the clipboard.";
        } catch (error) {
            output.focus();
            output.select();
            message.textContent = "Manifest selected. Copy it with the browser copy command.";
        }
    });

    document.getElementById("manifest-import").addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        try {
            const manifest = JSON.parse(await file.text());
            if (manifest.version !== 1) throw new Error("Unsupported manifest version.");
            if (manifest.projectId !== config.project.id) {
                throw new Error("Manifest project does not match this Studio.");
            }
            if (manifest.zinePath !== config.zinePath) {
                throw new Error("Manifest publication path does not match this Studio.");
            }
            if (manifest.sourceReference?.zineSha256 !== config.sourceReference.zineSha256) {
                throw new Error("Manifest source is stale; rebuild Studio before importing.");
            }

            if (manifest.format === "zineos-asset-placement") {
                if (!Array.isArray(manifest.placements)) throw new Error("Asset placements are missing.");
                const unknown = manifest.placements.find((imported) => !slotRegistry.has(imported.key));
                if (unknown) throw new Error(`Unknown asset target: ${unknown.key}`);
                manifest.placements.forEach((imported) => {
                    const slot = slotRegistry.get(imported.key).slot;
                    if (
                        imported.pageUnitId !== slot.pageUnitId
                        || imported.kind !== slot.kind
                        || imported.blockId !== (slot.blockId || null)
                        || imported.assetId !== (slot.assetId || null)
                        || imported.assetIndex !== (slot.assetIndex ?? null)
                        || imported.cellIndex !== (slot.cellIndex ?? null)
                    ) {
                        throw new Error(`Asset target evidence mismatch: ${imported.key}`);
                    }
                    if (
                        imported.previewDataUrl !== null
                        && imported.previewDataUrl !== undefined
                        && !/^data:image\/(jpeg|png|webp);base64,/.test(imported.previewDataUrl)
                    ) {
                        throw new Error(`Unsafe asset preview data: ${imported.key}`);
                    }
                });

                manifest.placements.forEach((imported) => {
                    placementState.set(imported.key, {...imported, dirty: true});
                    const registered = slotRegistry.get(imported.key);
                    if (imported.previewDataUrl) installImage(registered, imported.previewDataUrl);
                    applyPlacement(registered);
                });
                message.textContent = `${manifest.placements.length} placements imported.`;
            } else if (manifest.format === "zineos-text-placement") {
                if (!Array.isArray(manifest.edits)) throw new Error("Text edits are missing.");
                const unknown = manifest.edits.find((imported) => !textRegistry.has(imported.key));
                if (unknown) throw new Error(`Unknown text target: ${unknown.key}`);
                manifest.edits.forEach((imported) => {
                    const registered = textRegistry.get(imported.key);
                    if (
                        imported.pageUnitId !== registered.slot.pageUnitId
                        || imported.blockId !== registered.slot.blockId
                        || (imported.field || "content") !== registered.slot.field
                    ) {
                        throw new Error(`Text target evidence mismatch: ${imported.key}`);
                    }
                    if (imported.originalText !== registered.slot.originalText) {
                        throw new Error(`Original text mismatch: ${imported.key}`);
                    }
                });
                manifest.edits.forEach((imported) => {
                    const registered = textRegistry.get(imported.key);
                    const existing = ensureTextState(registered.slot, registered.element);
                    textState.set(imported.key, {
                        ...existing,
                        ...imported,
                        dirty: true,
                    });
                    applyTextEdit(registered);
                });
                message.textContent = `${manifest.edits.length} text edits imported.`;
            } else {
                throw new Error("Unsupported manifest format.");
            }

            refreshInspector();
        } catch (error) {
            message.textContent = `Manifest import failed: ${error.message}`;
        } finally {
            event.target.value = "";
        }
    });

    previewFrame.addEventListener("load", initializePreview, {once: true});
    previewFrame.srcdoc = previewSource;
})();
