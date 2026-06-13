echo
echo "=========================================================================================="
echo "Attempting to log in to azure and run pulumi to setup infrastructure..."

command -v pulumi >/dev/null 2>&1 || { echo "Pulumi is not installed. Please follow instructions in the README."; exit 0; }

az account show > /dev/null 2>&1 || az login
export ARM_CLIENT_ID=f6ff0da1-19e9-498d-af50-19db67779ed2
export ARM_SUBSCRIPTION_ID=9dce66e3-8b8f-4092-9f6d-d9525cd97d4c
export ARM_TENANT_ID=dc9249f1-89a1-4c43-8e22-c55df13f5937
export ARM_CLIENT_SECRET=$(az keyvault secret show --name "arm-client-secret" --vault-name ci-cd-secrets --query "value" -o tsv)
export AZURE_STORAGE_ACCOUNT=arataaicicd
export AZURE_STORAGE_KEY=$(az storage account keys list -g ci-cd -n arataaicicd --query "[?keyName=='key1'].value" -o tsv)
export PULUMI_BACKEND_URL=azblob://pulumi-state
export PULUMI_CONFIG_PASSPHRASE=
pushd pulumi
pulumi stack select dev || pulumi stack init dev
pulumi up --yes
popd

echo "=========================================================================================="
echo "Pulumi setup complete! You can now run the project locally using 'run_locally.sh' or run"
echo "individual workflows in the workflows/connector directory."
echo
echo "If you haven't already, add these environment variables to your .zshrc for future use:"
echo
echo export ARM_CLIENT_ID=f6ff0da1-19e9-498d-af50-19db67779ed2
echo export ARM_SUBSCRIPTION_ID=9dce66e3-8b8f-4092-9f6d-d9525cd97d4c
echo export ARM_TENANT_ID=dc9249f1-89a1-4c43-8e22-c55df13f5937
echo export ARM_CLIENT_SECRET=$(az keyvault secret show --name "arm-client-secret" --vault-name ci-cd-secrets --query "value" -o tsv)
echo export AZURE_STORAGE_ACCOUNT=arataaicicd
echo export AZURE_STORAGE_KEY=$(az storage account keys list -g ci-cd -n arataaicicd --query "[?keyName=='key1'].value" -o tsv)
echo export PULUMI_BACKEND_URL=azblob://pulumi-state
echo export PULUMI_CONFIG_PASSPHRASE=

rm setup_pulumi.sh
