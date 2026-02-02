import ReactMarkdown from "react-markdown";

const Markdown = ({ content, className = "" }) => {
  if (!content) {
    return <span className={className}>-</span>;
  }
  const classes = ["markdown-content", className].filter(Boolean).join(" ");
  return (
    <ReactMarkdown skipHtml className={classes}>
      {content}
    </ReactMarkdown>
  );
};

export default Markdown;
