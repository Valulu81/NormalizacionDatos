function filterNormalizedTable() {
      const estado = document.getElementById("sel-estado").value;
      const moneda = document.getElementById("sel-moneda").value;
      const fuente = document.getElementById("sel-fuente").value;
      const rows = [...document.querySelectorAll("#table-normalized tbody tr[data-estado]")];
      let visible = 0;
      rows.forEach((row) => {
        const matches = (estado === "Todos" || row.dataset.estado === estado)
          && (moneda === "Todas" || row.dataset.moneda === moneda)
          && (fuente === "Todas" || row.dataset.fuente === fuente);
        row.hidden = !matches;
        if (matches) visible += 1;
      });
      document.getElementById("normalized-counter").textContent =
        `${visible} de ${rows.length} transacciones visibles`;
    }

    function openUploadModal() {
      document.getElementById("modal-upload").classList.remove("hidden");
      document.getElementById("file-input").focus();
    }

    function closeUploadModal() {
      document.getElementById("modal-upload").classList.add("hidden");
    }

    function downloadTransactions() {
      const payload = buildExportPayload();
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = "transacciones_normalizadas.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    }

    function buildExportPayload() {
      return {
        transactions: JSON.parse(document.getElementById("export-transactions").textContent),
        invalid_records: {
          pending: invalidRecords.filter((record) => record.action === "pending").map(exportInvalidRecord),
          marked: invalidRecords.filter((record) => record.action === "marked").map(exportInvalidRecord),
          separated: invalidRecords.filter((record) => record.action === "separated").map(exportInvalidRecord)
        },
        discarded_count: invalidRecords.filter((record) => record.action === "discarded").length
      };
    }

    const invalidRecords = JSON.parse(document.getElementById("invalid-records").textContent);
    invalidRecords.forEach((record) => { record.action = "pending"; });

    function exportInvalidRecord(record) {
      return {
        position: record.position,
        source: record.source,
        original_json: record.original,
        errors: record.errors
      };
    }

    function createCell(row, className, content) {
      const cell = document.createElement("td");
      cell.className = className;
      cell.textContent = content;
      row.appendChild(cell);
      return cell;
    }

    function addActionButton(container, label, action, className) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.recordAction = action;
      button.className = className;
      button.textContent = label;
      container.appendChild(button);
    }

    function createInvalidRow(record, location) {
      const row = document.createElement("tr");
      row.className = "border-b border-outline-variant/60 align-top transition-colors hover:bg-surface-container-low/50";
      row.dataset.position = String(record.position);
      if (record.action === "marked") row.classList.add("bg-secondary-fixed/40");
      if (record.action === "discarded") row.classList.add("opacity-60");

      createCell(row, "py-4 px-5 font-medium text-tertiary font-mono text-sm", String(record.position));
      createCell(row, "py-4 px-5 font-mono text-tertiary", record.source);

      const originalCell = document.createElement("td");
      originalCell.className = "py-4 px-5";
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.className = "inline-flex items-center gap-1 text-tertiary hover:underline font-medium cursor-pointer";
      summary.textContent = "Ver registro";
      const original = document.createElement("pre");
      original.className = "mt-2 p-3 rounded-lg bg-surface-container text-xs font-mono text-on-surface border border-outline-variant/60 whitespace-pre-wrap break-all";
      original.textContent = record.original;
      details.append(summary, original);
      originalCell.appendChild(details);
      row.appendChild(originalCell);

      const reasonsCell = document.createElement("td");
      reasonsCell.className = "py-4 px-5";
      const reasons = document.createElement("ul");
      reasons.className = "list-disc list-inside space-y-1 text-tertiary text-xs leading-relaxed";
      record.errors.forEach((reason) => {
        const item = document.createElement("li");
        item.textContent = reason;
        reasons.appendChild(item);
      });
      reasonsCell.appendChild(reasons);
      row.appendChild(reasonsCell);

      const actionsCell = document.createElement("td");
      actionsCell.className = "py-4 px-5";
      const actions = document.createElement("div");
      actions.className = "inline-flex items-center gap-1.5 flex-wrap";
      if (location === "active") {
        addActionButton(actions, record.action === "marked" ? "Desmarcar" : "Marcar", "mark", "px-2.5 py-1.5 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high text-xs font-medium transition-colors");
        addActionButton(actions, "Separar", "separate", "px-2.5 py-1.5 rounded-lg bg-tertiary-fixed text-on-tertiary-fixed-variant hover:bg-tertiary hover:text-on-tertiary text-xs font-semibold transition-colors");
        addActionButton(actions, "Descartar", "discard", "px-2.5 py-1.5 rounded-lg border border-outline text-secondary hover:text-on-surface hover:bg-surface-container text-xs font-medium transition-colors");
      } else {
        addActionButton(actions, location === "separated" ? "Reintegrar" : "Deshacer descarte", "restore", "px-2.5 py-1.5 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high text-xs font-medium transition-colors");
      }
      actionsCell.appendChild(actions);
      row.appendChild(actionsCell);
      return row;
    }

    function renderInvalidRecords() {
      const activeBody = document.getElementById("invalid-records-body");
      if (!activeBody) return;
      const active = invalidRecords.filter((record) => record.action === "pending" || record.action === "marked");
      const separated = invalidRecords.filter((record) => record.action === "separated");
      const discarded = invalidRecords.filter((record) => record.action === "discarded");
      const renderRows = (body, records, location) => {
        body.replaceChildren(...records.map((record) => createInvalidRow(record, location)));
      };
      renderRows(activeBody, active, "active");
      renderRows(document.getElementById("separated-records-body"), separated, "separated");
      renderRows(document.getElementById("discarded-records-body"), discarded, "discarded");
      document.getElementById("pending-count").textContent = String(
        invalidRecords.filter((record) => record.action === "pending").length
      );
      document.getElementById("marked-count").textContent = String(
        invalidRecords.filter((record) => record.action === "marked").length
      );
      document.getElementById("separated-count").textContent = String(separated.length);
      document.getElementById("discarded-count").textContent = String(discarded.length);
      document.getElementById("invalid-empty").classList.toggle("hidden", active.length > 0);
      document.getElementById("separated-section").classList.toggle("hidden", separated.length === 0);
      document.getElementById("discarded-section").classList.toggle("hidden", discarded.length === 0);
    }

    document.getElementById("invalid-records-body")?.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const button = event.target.closest("button[data-record-action]");
      if (!button) return;
      const record = invalidRecords.find(
        (item) => String(item.position) === button.closest("tr").dataset.position
      );
      if (!record) return;
      if (button.dataset.recordAction === "mark") {
        record.action = record.action === "marked" ? "pending" : "marked";
      } else if (button.dataset.recordAction === "separate") {
        record.action = "separated";
      } else if (button.dataset.recordAction === "discard") {
        record.action = "discarded";
      }
      renderInvalidRecords();
    });

    document.getElementById("separated-records-body")?.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const button = event.target.closest('button[data-record-action="restore"]');
      if (!button) return;
      const record = invalidRecords.find(
        (item) => String(item.position) === button.closest("tr").dataset.position
      );
      if (record) {
        record.action = "pending";
        renderInvalidRecords();
      }
    });

    document.getElementById("discarded-records-body")?.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const button = event.target.closest('button[data-record-action="restore"]');
      if (!button) return;
      const record = invalidRecords.find(
        (item) => String(item.position) === button.closest("tr").dataset.position
      );
      if (record) {
        record.action = "pending";
        renderInvalidRecords();
      }
    });

    const uploadForm = document.getElementById("upload-form");
    const fileInput = document.getElementById("file-input");
    const dropZone = document.getElementById("drop-zone");
    const fileError = document.getElementById("file-error");
    const selectedFile = document.getElementById("selected-file");

    document.querySelectorAll("#sel-estado, #sel-moneda, #sel-fuente").forEach((filter) => {
      filter.addEventListener("change", filterNormalizedTable);
    });

    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Element)) return;
      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) return;
      if (actionButton.dataset.action === "open-upload") {
        openUploadModal();
      } else if (actionButton.dataset.action === "close-upload") {
        closeUploadModal();
      } else if (actionButton.dataset.action === "download") {
        downloadTransactions();
      }
    });

    function showSelectedFile(file) {
      fileError.classList.add("hidden");
      if (!file) {
        selectedFile.textContent = "Ningún archivo seleccionado";
        return;
      }
      if (!file.name.toLowerCase().endsWith(".json")) {
        fileInput.value = "";
        selectedFile.textContent = "Ningún archivo seleccionado";
        fileError.textContent = "Selecciona un archivo con extensión .json.";
        fileError.classList.remove("hidden");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        fileInput.value = "";
        selectedFile.textContent = "Ningún archivo seleccionado";
        fileError.textContent = "El archivo supera el límite de 10 MB.";
        fileError.classList.remove("hidden");
        return;
      }
      selectedFile.textContent = file.name;
    }

    fileInput.addEventListener("change", () => showSelectedFile(fileInput.files[0]));
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("border-primary", "bg-surface-container");
      });
    });
    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("border-primary", "bg-surface-container");
      });
    });
    dropZone.addEventListener("drop", (event) => {
      const [file] = event.dataTransfer.files;
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput.files = transfer.files;
      showSelectedFile(file);
    });
    uploadForm.addEventListener("submit", (event) => {
      const file = fileInput.files[0];
      if (!file || !file.name.toLowerCase().endsWith(".json") || file.size > 10 * 1024 * 1024) {
        event.preventDefault();
        if (!file) {
          fileError.textContent = "Selecciona un archivo JSON para continuar.";
          fileError.classList.remove("hidden");
        } else {
          showSelectedFile(file);
        }
      }
    });
    document.getElementById("modal-upload").addEventListener("click", (event) => {
      if (event.target.id === "modal-upload") closeUploadModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeUploadModal();
    });
    renderInvalidRecords();
    filterNormalizedTable();
