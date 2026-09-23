# make_prisma_flowchart.R
# Consolidated cognitive-search PRISMA 2020 flow diagram.
#
# Regenerates the flow diagram from the filled PRISMA2020 template
# (PRISMA_cognitive_data.csv) using the official CRAN package.
#
# One-time setup:
#   install.packages("PRISMA2020")
#
# Then, from this folder:
#   Rscript make_prisma_flowchart.R
# (or source() it in RStudio)

library(PRISMA2020)

csv_file <- "PRISMA_cognitive_data.csv"      # filled PRISMA2020 template
data     <- PRISMA_data(read.csv(csv_file, stringsAsFactors = FALSE))

plot <- PRISMA_flowdiagram(
  data,
  interactive       = FALSE,
  previous          = FALSE,   # no earlier version of the review
  other             = TRUE,    # keep the "other methods" (Google Scholar Labs) arm
  detail_databases  = TRUE,    # list the four cognitive runs under the databases box
  side_boxes        = TRUE,    # Identification / Screening / Included side labels
  fontsize          = 15
)

# Save vector PDF (drop-in for the manuscript) and a raster PNG preview.
PRISMA_save(plot, filename = "PRISMA_flow_cognitive_R.pdf", filetype = "PDF", overwrite = TRUE)
PRISMA_save(plot, filename = "PRISMA_flow_cognitive_R.png", filetype = "PNG", overwrite = TRUE)

# For an editable/clickable version, uncomment:
# plot_i <- PRISMA_flowdiagram(data, interactive = TRUE, previous = FALSE,
#                              other = TRUE, detail_databases = TRUE)
# PRISMA_save(plot_i, filename = "PRISMA_flow_cognitive_R.html", filetype = "html", overwrite = TRUE)

cat("Done. Wrote PRISMA_flow_cognitive_R.pdf and .png\n")
