export default function (eleventyConfig) {
	eleventyConfig.addPassthroughCopy("docs/img/");
	eleventyConfig.addPassthroughCopy("docs/css/");
	eleventyConfig.addShortcode("year", () => `${new Date().getFullYear()}`);

	return {
		dir: {
			input: "docs",
		},
	};
}
