import os
import sys
from pdf2image import convert_from_path

def save_pdf_pages_as_images(pdf_path, output_dir=None):
    # Ensure the PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: The file '{pdf_path}' does not exist.")
        return

    # Extract the base name of the PDF (without extension)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Create an output directory named after the PDF
    output_folder = output_dir if output_dir else pdf_name
    os.makedirs(output_folder, exist_ok=True)

    # Convert the PDF pages to images
    images = convert_from_path(pdf_path)

    # Save each page as an image
    for i, image in enumerate(images, start=1):
        image_path = os.path.join(output_folder, f"{i}.png")
        image.save(image_path, "PNG")
        print(f"Saved: {image_path}")

    print(f"All pages saved successfully in '{output_folder}'.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <pdf_path> [output_directory]")
    else:
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        save_pdf_pages_as_images(pdf_path, output_dir)
