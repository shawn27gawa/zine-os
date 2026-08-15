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
    const freeLayerControls = document.getElementById("free-layer-controls");
    const slotRegistry = new Map();
    const placementState = new Map();

    let selectedKey = null;
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
        if (!selectedKey || !slotRegistry.has(selectedKey)) {
            controls.hidden = true;
            selectionLabel.textContent = "Select an image slot.";
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

        selectedKey = key;
        const registered = slotRegistry.get(key);
        registered.element.classList.add("studio-selected-slot");
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
        });

        buildNavigation(articles);
        message.textContent = "Studio ready. Drop photographs onto outlined slots.";
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
        if (!selectedKey) return;
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
        if (!selectedKey) return;
        const registered = slotRegistry.get(selectedKey);
        const state = ensureState(registered.slot);
        state.settings[getModeKey()] = defaultPlacement(registered.slot);
        state.dirty = true;
        applyPlacement(registered);
        refreshInspector();
    });

    document.getElementById("slot-file-input").addEventListener("change", async (event) => {
        if (!selectedKey) return;
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

    const manifestData = () => ({
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

    document.getElementById("manifest-export").addEventListener("click", () => {
        const manifest = manifestData();

        if (manifest.placements.length === 0) {
            message.textContent = "No placement changes to export.";
            return;
        }

        const manifestText = JSON.stringify(manifest, null, 2);
        const handoff = document.getElementById("manifest-handoff");
        const output = document.getElementById("manifest-output");
        const download = document.getElementById("manifest-download");

        if (manifestObjectUrl) URL.revokeObjectURL(manifestObjectUrl);
        manifestObjectUrl = URL.createObjectURL(
            new Blob([manifestText], {type: "application/json"})
        );

        output.value = manifestText;
        download.href = manifestObjectUrl;
        download.download = `${config.project.id}-asset-placement.json`;
        handoff.hidden = false;
        message.textContent = `${manifest.placements.length} placements prepared for Builder review.`;
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
            if (manifest.format !== "zineos-asset-placement" || manifest.version !== 1) {
                throw new Error("Unsupported manifest format.");
            }

            manifest.placements.forEach((imported) => {
                if (!slotRegistry.has(imported.key)) return;
                placementState.set(imported.key, {...imported, dirty: true});
                const registered = slotRegistry.get(imported.key);
                if (imported.previewDataUrl) installImage(registered, imported.previewDataUrl);
                applyPlacement(registered);
            });
            message.textContent = `${manifest.placements.length} placements imported.`;
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
