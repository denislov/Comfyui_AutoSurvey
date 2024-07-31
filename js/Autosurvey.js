import {app} from "/scripts/app.js";
import {api} from "/scripts/api.js";

app.registerExtension({
    name: "Comfy.Autosurvey",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // --- UploadFiles
        if (nodeData.name === "UploadFiles") {
            async function uploadFile(file) {
                try {
                    // Wrap file in formdata so it includes filename
                    const body = new FormData();
                    body.append("file", file);
                    const resp = await api.fetchApi("/upload/files", {
                        method: "POST",
                        body,
                    });

                    if (resp.status === 200) {
                        return await resp.json()
                    } else {
                        alert(resp.status + " - " + resp.statusText);
                    }
                } catch (error) {
                    alert(error);
                }
            }

            // Node Created
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const ret = onNodeCreated
                    ? onNodeCreated.apply(this, arguments)
                    : undefined;

                let UploadFiles = app.graph._nodes.filter(
                        (wi) => wi.type == nodeData.name
                    ),
                    nodeName = `${nodeData.name}_${UploadFiles.length}`;
                console.log(`Create ${nodeData.name}: ${nodeName}`);
                const showResult = this.widgets[0]
                showResult.inputEl.readOnly = true

                Object.defineProperty(showResult, "files", {
                    get: function () {
                        if (this._files) {
                            return this._files
                        } else {
                            return []
                        }
                    },
                    set: function (files) {
                        if (files instanceof FileList)
                            this._files = files
                    },
                    enumerable: true,
                    configurable: true
                })

                let uploadWidget;

                const fileInput = document.createElement("input");
                Object.assign(fileInput, {
                    type: "file",
                    accept: "image/jpeg,application/pdf",
                    multiple: true,
                    style: "display: none",
                    onchange: async () => {
                        if (fileInput.files.length) {
                            for (let i = 0; i < fileInput.files.length; i++) {
                                const data = await uploadFile(fileInput.files[i]);
                            }
                            showResult.files = fileInput.files
                            requestAnimationFrame(() => {
                                if (showResult.files) {
                                    const fileNames = Array.from(showResult.files).map(file => file.name);
                                    showResult.value = fileNames.join('\n')
                                }
                            })
                        }
                    },
                });
                document.body.append(fileInput);
                uploadWidget = this.addWidget("button", "upload_file", "files", () => {
                    fileInput.click();
                });
                uploadWidget.label = "choose file to upload";
                uploadWidget.serialize = false;

                return ret;
            };
            // Function set value


            // onExecuted

            // onConfigure

        }
        // --- UploadFiles
    },
});
