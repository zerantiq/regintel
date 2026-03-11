resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'polyglotstore'
  location: resourceGroup().location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}
