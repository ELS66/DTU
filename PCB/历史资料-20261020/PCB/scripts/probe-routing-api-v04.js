if((await eda.dmt_SelectControl.getCurrentDocumentInfo())?.uuid!=="4211128ecf040c100b33238447713203")throw Error("Wrong PCB");return {autoRoutingAvailable:typeof eda.pcb_Document.autoRouting};
