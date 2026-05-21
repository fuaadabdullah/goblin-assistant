import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogClose,
  DialogOverlay,
} from '../Dialog';

function renderOpenDialog(extra?: React.ReactNode) {
  return render(
    <Dialog defaultOpen>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm action</DialogTitle>
          <DialogDescription>Are you sure?</DialogDescription>
        </DialogHeader>
        <p>Body content</p>
        <DialogFooter>
          <DialogClose>Cancel</DialogClose>
          {extra}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

describe('Dialog', () => {
  it('renders trigger before opening', () => {
    render(
      <Dialog>
        <DialogTrigger>Open me</DialogTrigger>
        <DialogContent>
          <DialogTitle>Hidden</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByText('Open me')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens when the trigger is clicked', () => {
    render(
      <Dialog>
        <DialogTrigger>Open me</DialogTrigger>
        <DialogContent>
          <DialogTitle>Now visible</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    fireEvent.click(screen.getByText('Open me'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Now visible')).toBeInTheDocument();
  });

  it('renders title, description, and body when open', () => {
    renderOpenDialog();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Confirm action')).toBeInTheDocument();
    expect(screen.getByText('Are you sure?')).toBeInTheDocument();
    expect(screen.getByText('Body content')).toBeInTheDocument();
  });

  it('exposes an accessible close affordance', () => {
    renderOpenDialog();
    expect(screen.getByText('Close')).toHaveClass('sr-only');
  });

  it('closes when the built-in close button is clicked', () => {
    renderOpenDialog();
    const closeButton = screen.getByText('Close').closest('button');
    expect(closeButton).not.toBeNull();
    fireEvent.click(closeButton!);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('closes when DialogClose child is clicked', () => {
    renderOpenDialog();
    fireEvent.click(screen.getByText('Cancel'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('applies custom className to DialogContent', () => {
    render(
      <Dialog defaultOpen>
        <DialogContent className="custom-content">
          <DialogTitle>Styled</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByRole('dialog').className).toContain('custom-content');
  });

  it('applies custom className to DialogTitle and DialogDescription', () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle className="title-class">Title</DialogTitle>
          <DialogDescription className="desc-class">Desc</DialogDescription>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByText('Title').className).toContain('title-class');
    expect(screen.getByText('Desc').className).toContain('desc-class');
  });

  it('DialogHeader and DialogFooter accept className and children', () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>T</DialogTitle>
          <DialogHeader className="header-class">
            <span data-testid="header-child">H</span>
          </DialogHeader>
          <DialogFooter className="footer-class">
            <span data-testid="footer-child">F</span>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByTestId('header-child').parentElement?.className).toContain('header-class');
    expect(screen.getByTestId('footer-child').parentElement?.className).toContain('footer-class');
  });

  it('calls onOpenChange when state transitions', () => {
    const onOpenChange = jest.fn();
    render(
      <Dialog onOpenChange={onOpenChange}>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Tracked</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    fireEvent.click(screen.getByText('Open'));
    expect(onOpenChange).toHaveBeenCalledWith(true);
  });

  it('DialogOverlay accepts className', () => {
    render(
      <Dialog defaultOpen>
        <DialogOverlay className="overlay-class" data-testid="overlay" />
        <DialogContent>
          <DialogTitle>x</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    expect(screen.getByTestId('overlay').className).toContain('overlay-class');
  });
});
