import kagglehub

my_dataset = "./dataset"
download_path = kagglehub.dataset_download("yasserhessein/the-kvasir-dataset", output_dir=my_dataset)
print("Path to dataset files:", download_path)
