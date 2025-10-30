domain = "price_comparison_shopping"
description = """
Comparing product prices across multiple retailers with location-based cost analysis and purchase recommendations
"""
main_pipe = "pricegenius_workflow"

[concept.ApiResponse]
description = "Raw JSON response from an external API endpoint."
refines = "Text"

[concept.ProductOffer]
description = "A single product purchasing option from a retailer."

[concept.ProductOffer.structure]
store = { type = "text", description = "Name of the retailer or store", required = true }
price = { type = "number", description = "Product price in dollars", required = true }
url = { type = "text", description = "Link to the product page", required = true }
type = { type = "text", description = "Purchase type (online or in-store)", required = true }

[concept.EnrichedProductOffer]
description = "A product purchasing option with calculated distance and effective cost."

[concept.EnrichedProductOffer.structure]
store = { type = "text", description = "Name of the retailer or store", required = true }
price = { type = "number", description = "Product price in dollars", required = true }
url = { type = "text", description = "Link to the product page", required = true }
type = { type = "text", description = "Purchase type (online or in-store)", required = true }
distance_miles = { type = "number", description = "Driving distance from San Francisco downtown to physical store location" }
effective_cost = { type = "number", description = "Total cost including price and travel cost (price + distance_miles * 0.65)", required = true }

[concept.PurchaseAnalysis]
description = "LLM-generated analysis of product purchasing options with recommendation."

[concept.PurchaseAnalysis.structure]
best_option = { type = "text", description = "The recommended store and purchase method", required = true }
reasoning = { type = "text", description = "Explanation of why this option saves more money", required = true }
buy_recommendation = { type = "text", description = "Suggestion to buy online or go in person", required = true }

[concept.ComparisonTable]
description = "Structured table comparing all product offers with their costs and distances."
refines = "Text"

[concept.ImagePrompt]
description = "Text prompt for generating an image using an image generation model."
refines = "Text"

[concept.PriceGeniusResult]
description = "Final output containing the best purchasing option, analysis, comparison data, and visual summary."

[concept.PriceGeniusResult.structure]
best_option = { type = "text", description = "The recommended store and purchase method", required = true }
reasoning = { type = "text", description = "Explanation of the recommendation", required = true }
comparison_table = { type = "text", description = "Table of all options with store, price, distance, and effective cost", required = true }
summary_card = { type = "text", description = "Visual summary card image", required = true }

[pipe.pricegenius_workflow]
type = "PipeSequence"
description = """
Main orchestrator for the complete PriceGenius workflow: fetches product prices from multiple sources, enriches with distance data, analyzes options, and generates final output with recommendation and visual summary
"""
inputs = { product_name = "Text" }
output = "PriceGeniusResult"
steps = [
    { pipe = "fetch_all_prices_parallel", result = "all_raw_responses" },
    { pipe = "parse_all_results_sequence", result = "all_offers" },
    { pipe = "enrich_offers_batch", result = "enriched_offers" },
    { pipe = "analyze_and_visualize_sequence", result = "analysis_and_visuals" },
    { pipe = "assemble_final_output", result = "pricegenius_result" },
]

[pipe.fetch_all_prices_parallel]
type = "PipeParallel"
description = "Fetch prices from all three sources concurrently"
inputs = { product_name = "Text" }
output = "ApiResponse[]"
parallels = [
    { pipe = "fetch_bestbuy_prices", result = "bestbuy_raw_response" },
    { pipe = "fetch_walmart_prices", result = "walmart_raw_response" },
    { pipe = "fetch_serpapi_prices", result = "serpapi_raw_response" },
]
add_each_output = true
combined_output = "ApiResponse"

[pipe.fetch_bestbuy_prices]
type = "PipeExtract"
description = "Query Best Buy Product API for product prices"
inputs = { product_name = "Text" }
output = "Page[]"
model = "extract_text_from_visuals"

[pipe.fetch_serpapi_prices]
type = "PipeExtract"
description = "Query SerpAPI Google Shopping for product prices"
inputs = { product_name = "Image" }
output = "Page[]"
model = "extract_text_from_visuals"

[pipe.fetch_walmart_prices]
type = "PipeExtract"
description = "Query Walmart Product API for product prices"
inputs = { product_name = "Text" }
output = "Page[]"
model = "extract_text_from_visuals"

[pipe.parse_all_results_sequence]
type = "PipeSequence"
description = "Parse all API responses into structured offers sequentially"
inputs = { bestbuy_raw_response = "ApiResponse", walmart_raw_response = "ApiResponse", serpapi_raw_response = "ApiResponse" }
output = "ProductOffer[]"
steps = [
    { pipe = "parse_bestbuy_results", result = "bestbuy_offers" },
    { pipe = "parse_walmart_results", result = "walmart_offers" },
    { pipe = "parse_serpapi_results", result = "serpapi_offers" },
    { pipe = "merge_all_offers", result = "parsed_results" },
]

[pipe.parse_bestbuy_results]
type = "PipeLLM"
description = "Parse Best Buy API response into structured product offers"
inputs = { bestbuy_raw_response = "ApiResponse" }
output = "ProductOffer[]"
model = "llm_to_analyze_data"
system_prompt = """
You are a data parsing assistant. Your task is to parse JSON API responses and extract structured product offer information. Output the data as a structured list of ProductOffer objects.
"""
prompt = """
Parse the following Best Buy API response and extract all product offers.

@bestbuy_raw_response

Extract each product offer with the store name, price, product URL, and purchase type (online or in-store).
"""

[pipe.parse_walmart_results]
type = "PipeLLM"
description = "Parse Walmart API response into structured product offers"
inputs = { walmart_raw_response = "ApiResponse" }
output = "ProductOffer[]"
model = "llm_to_analyze_data"
system_prompt = """
You are a data parsing assistant. Your task is to parse raw API responses and extract structured product offer information. Output a list of ProductOffer objects.
"""
prompt = """
Parse the following Walmart API response and extract all product offers.

@walmart_raw_response

Extract each product offer with the store name, price, product URL, and purchase type (online or in-store).
"""

[pipe.parse_serpapi_results]
type = "PipeLLM"
description = "Parse SerpAPI response into structured product offers"
inputs = { serpapi_raw_response = "ApiResponse" }
output = "ProductOffer[]"
model = "llm_to_analyze_data"
system_prompt = """
You are a data parsing assistant. Your task is to extract structured product offer information from API responses. You will generate a list of ProductOffer objects.
"""
prompt = """
Parse the following SerpAPI response and extract all product offers into a structured list.

@serpapi_raw_response

Extract each product offer you find in the response.
"""

[pipe.merge_all_offers]
type = "PipeLLM"
description = "Combine all parsed offers from different sources into a single list"
inputs = { bestbuy_offers = "ProductOffer[]", walmart_offers = "ProductOffer[]", serpapi_offers = "ProductOffer[]" }
output = "ProductOffer[]"
model = "llm_to_answer_easy_questions"
system_prompt = """
You are a data processing assistant. Your task is to merge multiple lists of ProductOffer objects into a single unified list. Output the result as a structured list of ProductOffer objects.
"""
prompt = """
Combine all the product offers from the following sources into a single unified list:

Best Buy offers:
@bestbuy_offers

Walmart offers:
@walmart_offers

SerpAPI offers:
@serpapi_offers

Merge all these offers into one complete list, preserving all the information from each offer.
"""

[pipe.enrich_offers_batch]
type = "PipeBatch"
description = "Enrich each offer with distance from Google Maps API and effective cost calculation"
inputs = { all_offers = "ProductOffer[]" }
output = "EnrichedProductOffer[]"
branch_pipe_code = "enrich_single_offer"
input_list_name = "all_offers"
input_item_name = "offer"

[pipe.enrich_single_offer]
type = "PipeSequence"
description = "Fetch distance and calculate effective cost for a single offer"
inputs = { offer = "ProductOffer" }
output = "EnrichedProductOffer"
steps = [
    { pipe = "fetch_store_distance", result = "distance_data" },
    { pipe = "calculate_effective_cost", result = "enriched_offer" },
]

[pipe.fetch_store_distance]
type = "PipeExtract"
description = "Fetch driving distance from SF downtown to store using Google Maps Distance Matrix API"
inputs = { offer = "Image" }
output = "Page[]"
model = "extract_text_from_visuals"

[pipe.calculate_effective_cost]
type = "PipeLLM"
description = "Parse distance response and compute effective cost (price + distance_miles * 0.65)"
inputs = { offer = "ProductOffer", distance_response = "DistanceResponse" }
output = "EnrichedProductOffer"
model = "llm_to_analyze_data"
system_prompt = """
You are a data processing assistant. Your task is to parse distance information and calculate effective costs for product offers. You will generate a structured EnrichedProductOffer object.
"""
prompt = """
Given the following product offer and distance response, parse the distance information and calculate the effective cost.

@offer

@distance_response

Instructions:
- Extract the distance in miles from the distance_response
- If the offer type is "online" or if distance information is unavailable, set distance_miles to null
- Calculate effective_cost = price + (distance_miles * 0.65) for physical stores
- For online offers, effective_cost = price
- Preserve all original offer fields (store, price, url, type)
- Add the distance_miles and effective_cost fields
"""

[pipe.analyze_and_visualize_sequence]
type = "PipeSequence"
description = "Analyze offers, prepare comparison, and generate visual summary"
inputs = { enriched_offers = "EnrichedProductOffer[]", product_name = "Text" }
output = "Image"
steps = [
    { pipe = "rank_and_analyze", result = "analysis" },
    { pipe = "prepare_comparison_table", result = "comparison_table" },
    { pipe = "generate_card_prompt", result = "card_prompt" },
    { pipe = "generate_summary_card", result = "summary_card" },
]

[pipe.rank_and_analyze]
type = "PipeLLM"
description = "Analyze all enriched offers, rank by effective cost, and provide recommendation"
inputs = { enriched_offers = "EnrichedProductOffer[]", product_name = "Text" }
output = "PurchaseAnalysis"
model = "llm_to_analyze_data"
system_prompt = """
You are a shopping analyst that helps users find the best purchasing options. You analyze product offers considering both price and travel costs to provide data-driven recommendations. You will generate a structured PurchaseAnalysis output.
"""
prompt = """
Analyze the following product offers for: $product_name

@enriched_offers

Your task:
1. Rank all offers by their effective_cost (lowest to highest)
2. Identify the best option that saves the most money
3. Explain clearly why this option is the most cost-effective
4. Provide a clear recommendation on whether to buy online or go to a physical store

Consider both the base price and travel costs (for in-store purchases) in your analysis.
"""

[pipe.prepare_comparison_table]
type = "PipeLLM"
description = "Format enriched offers into a structured comparison table"
inputs = { enriched_offers = "EnrichedProductOffer[]" }
output = "ComparisonTable"
model = "llm_to_analyze_data"
system_prompt = """
You are a data formatting assistant. Your task is to transform structured product offer data into a well-formatted comparison table. The output should be a structured ComparisonTable object.
"""
prompt = """
Format the following enriched product offers into a clear, structured comparison table:

@enriched_offers

Create a table that displays all offers with their key information: store name, price, purchase type, distance (if applicable), and effective cost. Make it easy to compare all options at a glance.
"""

[pipe.generate_card_prompt]
type = "PipeLLM"
description = "Create image generation prompt for summary card with best option and price difference"
inputs = { analysis = "PurchaseAnalysis", comparison_table = "ComparisonTable", product_name = "Text" }
output = "Text"
model = "llm_for_creative_writing"
system_prompt = """
You are an expert at creating concise, effective image generation prompts. Focus on visual elements, layout, and key information that should appear in the image.
"""
prompt = """
Create a VERY concise image generation prompt for a 512x512 summary card that visualizes the best purchasing option for $product_name.

@analysis

@comparison_table

The prompt should:
- Be extremely focused and concise (best practice for image generation)
- Specify a clean, modern card design with clear typography
- Include the best option, price difference/savings prominently
- Request relevant retailer logos or icons
- Emphasize readability and visual hierarchy
- Use specific visual design terms

Output only the image generation prompt text.
"""

[pipe.generate_summary_card]
type = "PipeImgGen"
description = "Generate 512x512 PNG summary card visualizing the best purchasing option"
inputs = { card_prompt = "Text" }
output = "Image"
model = "gen_image_basic"

[pipe.assemble_final_output]
type = "PipeLLM"
description = "Combine analysis, comparison table, and summary card into final structured result"
inputs = { analysis = "PurchaseAnalysis", comparison_table = "ComparisonTable", summary_card = "Image" }
output = "PriceGeniusResult"
model = "llm_to_answer_easy_questions"
system_prompt = """
You are assembling a final structured result (PriceGeniusResult) by combining the purchase analysis, comparison table, and summary card image.
"""
prompt = """
Assemble the final result by combining the following components:

@analysis

@comparison_table

Summary card image:
$summary_card

Create a structured output that includes the best purchasing option, reasoning, comparison table, and the summary card.
"""
