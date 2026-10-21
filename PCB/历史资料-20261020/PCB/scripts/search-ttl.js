return (await eda.lib_Device.search("SN74LVC2T45",undefined,undefined,undefined,10,1)).map(x=>({uuid:x.uuid,libraryUuid:x.libraryUuid,name:x.name,footprint:x.footprintName,supplierId:x.supplierId}));
