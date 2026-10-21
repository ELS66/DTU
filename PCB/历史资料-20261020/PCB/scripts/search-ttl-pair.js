return (await eda.lib_Device.search("74AXP4T245",undefined,undefined,undefined,5,1)).map(x=>({uuid:x.uuid,libraryUuid:x.libraryUuid,name:x.name,footprint:x.footprintName,supplierId:x.supplierId}));
